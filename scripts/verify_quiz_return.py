"""Optional Playwright regression: study links must preserve the current quiz.

Build dist first. Requires Playwright; pass --browser-path for a system browser.
"""
from pathlib import Path
import argparse
import functools
import http.server
import json
import threading
from datetime import date
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def current_question(page):
    return page.evaluate("getPool().find(q => q.id === state.currentId)")


def answer(page, question, correct=False):
    kind = question["type"]
    if kind == "单选":
        letter = question["answer"] if correct else next(k for k in question["options"] if k != question["answer"])
        page.locator(f'[data-letter="{letter}"]').click()
    elif kind == "多选":
        letters = question["answer"] if correct else question["answer"][:1]
        if not correct and len(question["answer"]) == 1:
            letters = next(k for k in question["options"] if k != question["answer"])
        for letter in letters:
            page.locator(f'[data-letter="{letter}"]').click()
        page.locator("#submit-multi").click()
    elif kind == "判断":
        value = question["answer"] if correct else ("错误" if question["answer"] == "正确" else "正确")
        page.locator(f'[data-judge="{value}"]').click()
    elif kind == "填空":
        page.locator("#fill-input").fill(question["answer"] if correct else "未掌握")
        page.locator("#submit-fill").click()
    else:
        page.locator("#show-short").click()
        value = "掌握" if correct else "未掌握"
        page.locator(f'[data-short-grade="{value}"]').click()
    page.wait_for_selector(".feedback-label.ok" if correct else ".feedback-label.ng")


def run(browser_path=None):
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "dist"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    cases = [
        ("seq", {"topic": "analog-electronics.t07"}),
        ("seq", {"chapter": "data-structures.c07"}),
        ("rnd", {"topic": "analog-electronics.t07"}),
        ("priority", {"course": "计算机网络"}),
        ("wrong", {"topic": "analog-electronics.t07"}),
        ("review", {"topic": "analog-electronics.t07"}),
        ("fav", {"topic": "analog-electronics.t07"}),
    ]
    results = []
    errors = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**({"executable_path": browser_path} if browser_path else {}))
            for width in (390, 1280):
                for mode, scope in cases:
                    context = browser.new_context(viewport={"width": width, "height": 844}, service_workers="block")
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    if mode in ("wrong", "review", "fav"):
                        page.goto(base + "/quiz.html?" + urlencode({**scope, "mode": "seq"}))
                        page.wait_for_selector("#question-stem")
                        answer(page, current_question(page))
                        page.locator("#fav").click()
                    page.goto(base + "/quiz.html?" + urlencode({**scope, "mode": mode}))
                    page.wait_for_selector("#question-stem")
                    question = current_question(page)
                    if mode in ("wrong", "review"):
                        assert page.locator(".feedback-label").count() == 0, "Review must start with an unanswered attempt"
                        page.reload()
                        page.wait_for_selector("#question-stem")
                        assert current_question(page)["id"] == question["id"] and page.locator(".feedback-label").count() == 0
                    if not page.locator(".feedback-label").count():
                        answer(page, question)
                    before = page.evaluate("id => ({given:state.done[id],count:state.history[id].length})", question["id"])
                    page.locator('.repair-links a[href*="notes.html"]').first.click()
                    page.wait_for_selector(".chapter-link")
                    page.go_back()
                    page.wait_for_selector("#question-stem")
                    page.wait_for_function("id => state.currentId === id", arg=question["id"])
                    assert page.locator(".feedback-label.ng").count() == 1
                    page.reload()
                    page.wait_for_selector(".feedback-label.ng")
                    assert current_question(page)["id"] == question["id"]
                    assert page.evaluate("id => ({given:state.done[id],count:state.history[id].length})", question["id"]) == before
                    page.locator("#next").click()
                    if mode in ("seq", "rnd", "priority") and page.locator("#question-stem").count():
                        assert current_question(page)["id"] != question["id"], "Only Next should advance"
                    results.append({"width": width, "mode": mode, "scope": scope, "question": question["id"], "return_reload_next": "pass"})
                    context.close()
            # More than 80 due questions must not push the just-answered question off screen.
            context = browser.new_context(service_workers="block")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/quiz.html?" + urlencode({"course": "计算机网络", "mode": "home"}))
            page.wait_for_selector("[data-jump-mode=seq]")
            page.evaluate("""() => {
              for (const q of getScope().slice(0,100)) {state.done[q.id]=q.type==='简答'?'未掌握':q.answer;state.wrong[q.id]=1;}
              state.mode='review';resetPosition();render();
            }""")
            question = current_question(page)
            answer(page, question, correct=True)
            assert current_question(page)["id"] == question["id"] and page.locator(".feedback-label.ok").count() == 1
            assert page.evaluate("getPool().length") == 80
            page.locator("#next").click()
            assert current_question(page)["id"] != question["id"] and page.locator(".feedback-label").count() == 0
            results.append({"mode": "review", "due": 100, "keep_answered_question": "pass"})
            context.close()
            # Explicitly finishing a topic must not resurrect its last answered question on reload.
            context = browser.new_context(service_workers="block")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/quiz.html?topic=analog-electronics.t01&mode=seq")
            page.wait_for_selector("#question-stem")
            total = page.evaluate("getScope().length")
            for _ in range(total):
                answer(page, current_question(page), correct=True)
                page.locator("#next").click()
            page.wait_for_selector(".card.empty")
            assert not page.evaluate("history.state?.quizQuestion")
            page.reload()
            page.wait_for_selector(".card.empty")
            assert page.locator("#question-stem").count() == 0
            results.append({"mode": "seq", "finished_topic_reload_stays_finished": "pass"})
            context.close()
            browser.close()
    finally:
        server.shutdown()
    assert not errors, errors
    report = {"checks": results, "errors": errors}
    report_path = ROOT / "audit_reports" / f"刷题回看返回验证_{date.today().isoformat()}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": len(results), "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-path")
    run(parser.parse_args().browser_path)
