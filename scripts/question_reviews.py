"""Reviewed question corrections and new practice, kept outside generated data."""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"id", "type", "stem", "options", "answer", "accepted_answers", "explanation", "topic_id", "topic_source", "knowledge_point", "ability", "difficulty", "rubric", "max_score", "rubric_source", "subject", "chapter"}


def load_edits():
    edits = {}
    for path in sorted((ROOT / "staging").glob("audit_*_edits.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if not item.get("id") or item["id"] in edits or set(item) - FIELDS:
                raise ValueError(f"无效或重复题目修订：{path.name}: {item.get('id')}")
            edits[item["id"]] = item
    return edits


def apply_reviews(questions):
    edits = load_edits()
    removed = load_removals()
    result = []
    for question in questions:
        if question['id'] in removed:
            continue
        edit = edits.get(question['id'], {})
        item = {**question, **edit}
        changed_answer = {key: edit[key] for key in ('type', 'stem', 'options', 'answer') if key in edit}
        if changed_answer:
            payload = json.dumps(changed_answer, ensure_ascii=False, sort_keys=True).encode('utf-8')
            item['answer_revision'] = 'audit-' + hashlib.sha256(payload).hexdigest()[:12]
        result.append(item)
    return result


def load_removals():
    removed = set()
    for path in sorted((ROOT / "staging").glob("audit_*_removals.json")):
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"删除题号必须是字符串数组：{path.name}")
        removed.update(values)
    return removed


def load_additions():
    questions = []
    for path in sorted((ROOT / "staging").glob("audit_*_additions.json")):
        for question in json.loads(path.read_text(encoding="utf-8")):
            question = dict(question)
            if not question["id"].startswith("gap-"):
                question["id"] = "gap-" + question["id"]
            question["source"] = "课程缺口补充"
            question["topic_source"] = "manual"
            questions.append(question)
    return questions


def load_gap_questions():
    base = json.loads((ROOT / "staging" / "course_gap_questions.json").read_text(encoding="utf-8"))
    return apply_reviews(base + load_additions())
