"""Optional browser acceptance for every topic, card and filtered practice pool."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import quote

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


def main(browser_path, course_name=None, report_path="audit_reports/全量验收_知识点浏览器_2026-10-15.json"):
    courses = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))["courses"]
    if course_name:
        courses = [course for course in courses if course["course_name"] == course_name]
        assert courses, course_name
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "dist")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    cards, pools, errors = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=browser_path, headless=True)
            for width, theme in [(390, "light"), (390, "dark"), (1280, "light"), (1280, "dark")]:
                context = browser.new_context(viewport={"width": width, "height": 844}, color_scheme=theme, service_workers="block")
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                quiz = context.new_page() if width == 390 and theme == "light" else None
                if quiz:
                    quiz.on("pageerror", lambda error: errors.append(str(error)))
                for course in courses:
                    page.goto(base + "/color-notes.html#course=" + quote(course["course_name"]))
                    page.wait_for_selector(".recall-card")
                    page.locator("#recall-toggle").click()
                    for topic in course["topics"]:
                        data = page.evaluate("""id => {
                          const point = [...document.querySelectorAll('.point[data-topic-id]')].find(p => p.dataset.topicId === id);
                          if (!point) return {id, missing: true};
                          const card = point.closest('.recall-card');
                          const section = point.closest('.chapter-section');
                          const ci = [...document.querySelectorAll('.chapter-section')].indexOf(section);
                          setActiveChapter(ci, {focus: false});
                          const index = [...section.querySelectorAll('.recall-card')].indexOf(card);
                          setActiveRecallCard(index, {focus: false});
                          document.querySelector('#reveal-card').click();
                          const rect = card.getBoundingClientRect();
                          return {id, title: point.textContent.trim(), chapter: ci,
                            visible: rect.width > 0 && rect.height > 0,
                            height: Math.round(rect.height), width: Math.round(rect.width),
                            overflow: document.documentElement.scrollWidth > innerWidth,
                            diagrams: [...card.querySelectorAll('.recall-diagram')].map(d => ({open: d.open})),
                            practice: card.querySelector('.point-practice-link')?.getAttribute('href')};
                        }""", topic["topic_id"])
                        data.update(viewport=width, theme=theme)
                        assert not data.get("missing") and data["visible"] and not data["overflow"], data
                        assert data["title"] == topic["title"] and data["practice"], data
                        if width == 390:
                            assert not any(d["open"] for d in data["diagrams"]), data
                            assert data["height"] <= 600, data
                        cards.append(data)
                        if quiz:
                            quiz.goto(base + "/" + data["practice"].removeprefix("./"))
                            quiz.wait_for_function("typeof getPool === 'function' && getPool().length > 0")
                            pool = quiz.evaluate("getPool().map(q => ({id:q.id, topic_id:q.topic_id}))")
                            assert all(q["topic_id"] == topic["topic_id"] for q in pool), (topic["topic_id"], pool)
                            pools.append({"topic_id": topic["topic_id"], "question_ids": [q["id"] for q in pool]})
                    print(width, theme, course["course_id"], "checked", flush=True)
                context.close()
            browser.close()
    finally:
        server.shutdown()
    assert not errors, errors
    report = {"build": (ROOT / "dist/build-meta.js").read_text(encoding="utf-8").split('"id":"')[1].split('"')[0], "card_contexts": len(cards), "topic_pools": len(pools), "max_phone_card_height": max(c["height"] for c in cards if c["viewport"] == 390), "errors": errors, "cards": cards, "pools": pools}
    (ROOT / report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"cards", "pools"}}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-path", default="C:/Program Files/Google/Chrome/Application/chrome.exe")
    parser.add_argument("--course")
    parser.add_argument("--report", default="audit_reports/全量验收_知识点浏览器_2026-10-15.json")
    args = parser.parse_args()
    main(args.browser_path, args.course, args.report)
