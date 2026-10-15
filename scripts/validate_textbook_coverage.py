"""Distinguish internal chapter consistency from external textbook coverage."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate(course_name=None, require_complete=False):
    coverage=json.loads((ROOT/'textbook-coverage.json').read_text(encoding='utf-8'))
    books=json.loads((ROOT/'textbook-map.json').read_text(encoding='utf-8'))
    expected={c['name'] for c in books['courses']}
    records=coverage['courses']
    learning=json.loads((ROOT/'learning-map.json').read_text(encoding='utf-8'))
    topics={t['topic_id']:t for c in learning['courses'] for t in c['topics']}
    questions={q['id']:q for q in json.loads((ROOT/'questions.json').read_text(encoding='utf-8'))}
    if {c['course'] for c in records}!=expected or len(records)!=len(expected):
        raise ValueError('External coverage records must match the course catalog')
    selected=[r for r in records if not course_name or r['course']==course_name]
    if not selected:raise ValueError(f'Unknown course: {course_name}')
    unresolved=[]
    for row in selected:
        file=(ROOT/row['review_file']).resolve()
        if ROOT not in file.parents or not file.is_file() or not row.get('source_urls'):
            raise ValueError(f'Missing external review: {row["course"]}')
        if row['status']!='accepted':
            unresolved.append(row['course'])
            continue
        proof=json.loads(file.read_text(encoding='utf-8'))
        if len(proof.get('rows',[]))!=row.get('section_count'):
            raise ValueError(f'Missing textbook sections: {row["course"]}')
        actual=[section['textbook_section'] for section in proof['rows']]
        if len(set(actual))!=len(actual) or set(actual)!=set(row.get('section_ids',[])):
            raise ValueError(f'Textbook section identities changed: {row["course"]}')
        for section in proof['rows']:
            if section.get('status')!='accepted' or not section.get('topic_ids') or not section.get('student_evidence',{}).get('beginner') or not section.get('student_evidence',{}).get('applied'):
                raise ValueError(f'Incomplete section review: {section.get("textbook_section")}')
            for topic_id in section['topic_ids']:
                if topic_id not in topics or topics[topic_id]['chapter_id']!=section['chapter_id']:
                    raise ValueError(f'Incorrect section topic: {topic_id}')
            if not section.get('question_ids') or any(qid not in questions or questions[qid]['topic_id'] not in section['topic_ids'] for qid in section['question_ids']):
                raise ValueError(f'Incorrect section practice: {section["textbook_section"]}')
            for role in ('beginner','applied'):
                evidence=section['student_evidence'][role]
                report=(ROOT/evidence['report']).resolve()
                if ROOT not in report.parents or not report.is_file() or not evidence.get('evidence'):
                    raise ValueError(f'Missing student evidence: {section["textbook_section"]}')
                review=json.loads(report.read_text(encoding='utf-8'))
                item=next((s for s in review.get('section_checks',[]) if s['textbook_section'].split()[0]==evidence['section']),None)
                if not item or item['status']!=evidence['status'] or any(word in item['status'] for word in ('pending','待复测','待新候选','阻断未修')):
                    raise ValueError(f'Unresolved student check: {section["textbook_section"]}')
    if unresolved:
        print('教材内容尚未完整验收：'+'、'.join(unresolved))
        print('上述课程仅有站内结构与已存在内容检查，不能宣称教材完整；具体缺口见外部覆盖报告。')
        if require_complete:raise ValueError('Textbook coverage has unresolved courses')
    else:print('所选课程外部教材覆盖与独立试学记录通过。')
    return unresolved


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course')
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    validate(args.course,args.require_complete)
