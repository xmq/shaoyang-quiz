"""Optional browser check: every course and practice opens on first offline use."""
import argparse
import functools
import http.server
import json
import re
import threading
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def main(browser_path, report_path='audit_reports/全量验收_离线_2026-10-15.json'):
    courses=json.loads((ROOT/'course-index.json').read_text(encoding='utf-8'))
    teaching_refs={p for folder in ['course_notes','color_notes'] for f in (ROOT/folder).glob('*.md') for p in re.findall(r'!\[[^]]*\]\(\.\./([^)]*)\)',f.read_text(encoding='utf-8'))}
    media_text=(ROOT/'question-media.js').read_text(encoding='utf-8')
    question_media=json.loads(media_text[media_text.index('{'):media_text.rfind('}')+1])
    question_refs={item['src'].removeprefix('./') for item in question_media.values()}
    refs=sorted(teaching_refs|question_refs)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[]; rows=[]; offline_question_image=False
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=browser_path,headless=True)
            context=browser.new_context(viewport={'width':390,'height':844})
            page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/'); page.evaluate('navigator.serviceWorker.ready')
            page.wait_for_function('navigator.serviceWorker.controller !== null')
            cached=page.evaluate('''async refs=>{const c=await caches.open((await caches.keys()).find(n=>n.startsWith('shaoyang-quiz-')));return {assets:(await c.keys()).length,missing:(await Promise.all(refs.map(async r=>await c.match('./'+r)?null:r))).filter(Boolean)}}''',refs)
            assert not cached['missing'],cached
            context.set_offline(True)
            for course in courses:
                for module in ['notes.html','color-notes.html']:
                    page.goto(base+'/'+module+'#course='+quote(course['name']))
                    page.wait_for_selector('.chapter-link')
                    assert page.locator('.chapter-section').count()>0
                    page.wait_for_function("[...document.querySelectorAll('.note-figure img')].every(i=>i.complete&&i.naturalWidth>0)")
                    image_count=page.locator('.note-figure img').count()
                    if image_count:
                        first=page.locator('.note-figure img').first
                        index=first.evaluate('e=>[...document.querySelectorAll(".chapter-section")].indexOf(e.closest(".chapter-section"))')
                        page.locator('#mobile-nav-toggle').click(); page.locator('.chapter-link').nth(index).click()
                        first.evaluate("e=>{const d=e.closest('details'); if(d)d.open=true}")
                        first.locator('..').click()
                        page.wait_for_function('imageViewer?.opener?.isOpen && imageViewer.currSlide.content.state==="loaded"')
                        page.locator('.pswp__button--zoom').click()
                        page.keyboard.press('Escape'); page.wait_for_selector('.pswp',state='detached')
                    rows.append({'course':course['name'],'module':module,'loaded_images':image_count,'offline':True,'viewer_checked':bool(image_count)})
                page.goto(base+'/quiz.html?course='+quote(course['name'])+'&mode=seq')
                page.wait_for_function("typeof getPool==='function' && getPool().length>0")
                if page.evaluate("getPool().some(q=>q.id==='cg-04-s3-q21')"):
                    page.evaluate("state.currentId='cg-04-s3-q21'; render()")
                    image=page.locator('.question-media img')
                    image.scroll_into_view_if_needed()
                    page.wait_for_function("document.querySelector('.question-media img')?.naturalWidth>0")
                    offline_question_image=True
                rows.append({'course':course['name'],'module':'quiz.html','offline':True,'questions':page.evaluate('getPool().length')})
                print(course['name'],'offline checked',flush=True)
            browser.close()
    finally:
        server.shutdown()
    assert not errors and offline_question_image,errors
    build=(ROOT/'dist/build-meta.js').read_text(encoding='utf-8').split('"id":"')[1].split('"')[0]
    report={'build':build,'teaching_assets':len(teaching_refs),'question_assets':len(question_refs),'offline_question_image':offline_question_image,'cached':cached,'pages':len(rows),'errors':errors,'results':rows}
    (ROOT/report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='results'},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
    parser.add_argument('--report',default='audit_reports/全量验收_离线_2026-10-15.json')
    args=parser.parse_args()
    main(args.browser_path,args.report)
