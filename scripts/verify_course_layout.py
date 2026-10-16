"""Browser regression for textbook regrouping and existing learning records."""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from verify_all_topic_links import QuietHandler

ROOT = Path(__file__).resolve().parents[1]
COURSE = '计算机组成原理'


def main(report_path='audit_reports/组成原理_旧进度迁移_2026-10-15.json'):
    course = next(c for c in json.loads((ROOT/'learning-map.json').read_text(encoding='utf-8'))['courses'] if c['course_name'] == COURSE)
    revision = course['layout_revision']
    old = course['previous_layout']
    topic_positions = {t['topic_id']: (index+1, card+1) for index, chapter in enumerate(course['chapters']) for card, t in enumerate([t for t in course['topics'] if t['chapter_id'] == chapter['chapter_id']])}
    ratings = {f'{COURSE}::{i+1}::{j+1}': {'value': 'known', 'level': j+1, 'nextReviewAt': '2020-01-01T00:00:00Z', 'savedAt': f'old-{topic}'} for i, chapter in enumerate(old) for j, topic in enumerate(chapter['topic_ids'])}
    ratings['计算机网络::2::1'] = {'value': 'fuzzy', 'savedAt': 'other'}
    progress = {COURSE: {'completed': [old[i]['chapter_id'] for i in (0,1,6)], 'lecture': [old[6]['chapter_id']], 'lastLectureChapter': 7}, '计算机网络': {'completed': ['computer-network.c01']}}
    quiz = {'done': {'gap-co-001': {'correct': True}}, 'fav': ['gap-co-001'], 'wrong': {'keep': True}}
    seed = {'shaoyang-recall-ratings-v2': ratings, 'shaoyang-reading-progress-v1': progress, 'shaoyang-last-learning': {'course': COURSE, 'module': 'color-notes', 'chapter': 3, 'card': 2}, 'shaoyang-quiz-v5': quiz, 'shaoyang-selected-course-v1': COURSE}
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, checks = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            context = browser.new_context(viewport={'width': 390, 'height': 844}, service_workers='block')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base+'/index.html')
            page.evaluate('(seed)=>{localStorage.clear();for(const [k,v] of Object.entries(seed))localStorage.setItem(k,typeof v === "string"?v:JSON.stringify(v))}', seed)
            page.reload()
            stored = page.evaluate('Object.fromEntries(Object.entries(localStorage).map(([k,v])=>[k,(()=>{try{return JSON.parse(v)}catch{return v}})()]))')
            migrated = stored['shaoyang-recall-ratings-v2']
            for i, chapter in enumerate(old):
                for j, topic in enumerate(chapter['topic_ids']):
                    new_chapter, card = topic_positions[topic]
                    assert migrated[f'{COURSE}::{new_chapter}::{card}'] == ratings[f'{COURSE}::{i+1}::{j+1}'], topic
            assert len([k for k in migrated if k.startswith(COURSE+'::')]) == 18
            assert migrated['计算机网络::2::1'] == ratings['计算机网络::2::1']
            assert stored['shaoyang-quiz-v5'] == quiz
            reading = stored['shaoyang-reading-progress-v1']
            assert reading[COURSE]['completed'] == ['computer-organization.c01']
            assert reading[COURSE]['previousLayoutProgress'] == progress[COURSE]
            assert reading[COURSE]['lastLectureChapter'] == 4
            assert reading['计算机网络'] == progress['计算机网络']
            recent = stored['shaoyang-last-learning']
            assert (recent['chapter'],recent['card']) == topic_positions['computer-organization.t07']
            checks += ['all 18 old ratings follow topic IDs; no new topic inherits mastery', 'quiz records and other courses preserved', 'old completions archived; expanded chapters require rereading', 'recent lesson moved by topic ID']
            links = page.locator('a[href*="notes.html"]').evaluate_all('(a)=>a.map(x=>x.href).filter(x=>decodeURIComponent(x).includes("计算机组成原理"))')
            assert links and all('layout='+revision in link for link in links), links
            checks.append('home, mobile and due-card links carry current layout revision')
            page.reload()
            assert page.evaluate('JSON.parse(localStorage.getItem("shaoyang-recall-ratings-v2"))') == migrated
            checks.append('migration is idempotent on reload')
            routes = [
                ('notes.html', '&chapter=3', 8, None),
                ('notes.html', '&chapter=3&layout='+revision, 3, None),
                ('color-notes.html', '&chapter=3&card=2', 7, 'computer-organization.t07'),
                ('color-notes.html', '&chapter=7&card=1', 4, 'computer-organization.t14'),
                ('color-notes.html', '&chapter=3&topic=computer-organization.t40', 6, 'computer-organization.t40'),
            ]
            for module, suffix, expected, topic in routes:
                page.goto(base+'/'+module+'#course='+quote(COURSE)+suffix)
                page.wait_for_selector('.chapter-section', state='attached')
                assert page.evaluate('activeChapterIndex+1') == expected, (module,suffix,page.url)
                if topic:
                    actual = page.evaluate('document.querySelectorAll(".chapter-section")[activeChapterIndex].querySelectorAll(".recall-card")[activeRecallIndex].querySelector(".point").dataset.topicId')
                    assert actual == topic, (module, suffix, actual, topic, page.url)
                checks.append({'route': module+suffix, 'chapter': expected, 'topic': topic})
            for topic in course['topics']:
                page.goto(base+'/color-notes.html#course='+quote(COURSE)+'&topic='+topic['topic_id'])
                page.wait_for_selector('.chapter-section', state='attached')
                expected_chapter, expected_card = topic_positions[topic['topic_id']]
                assert page.evaluate('[activeChapterIndex+1,activeRecallIndex+1]') == [expected_chapter,expected_card], topic
                page.reload()
                page.wait_for_selector('.chapter-section', state='attached')
                assert page.evaluate('[activeChapterIndex+1,activeRecallIndex+1]') == [expected_chapter,expected_card], topic
            checks.append(f'all {len(course["topics"])} topic links retain their card after refresh')
            page.goto(base+'/index.html')
            page.locator('a.home-course-main').filter(has_text=COURSE).click()
            page.wait_for_selector('.chapter-section', state='attached')
            page.go_back()
            assert page.url.endswith('/index.html'), page.url
            checks.append('browser native back returns from course to home')
            browser.close()
    finally:
        server.shutdown()
    assert not errors, errors
    report = {'build': (ROOT/'dist/build-meta.js').read_text(encoding='utf-8').split('"id":"')[1].split('"')[0], 'checks': checks, 'errors': errors, 'real_device': False}
    (ROOT/report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='audit_reports/组成原理_旧进度迁移_2026-10-15.json')
    main(parser.parse_args().report)
