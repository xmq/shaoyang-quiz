"""Merge reviewed adaptations of recent Hunan computer-job recall questions."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from question_reviews import apply_reviews

ROOT = Path(__file__).resolve().parents[1]
QUESTION_JSON = ROOT / "questions.json"
STAGING = ROOT / "staging" / "hunan_recall_questions.json"
PREFIX = "hn-recall-"
SOURCE = "湖南笔试回忆改编"
DERIVED_FIELDS = (
    "knowledge_point", "ability", "difficulty", "topic_id", "topic_title",
    "chapter_id", "required_depth", "topic_order", "rubric", "max_score", "rubric_source",
)


def add_confidence(question):
    item = dict(question)
    verified_event = str(item.get("id") or "").startswith(("hn-recall-sy26-", "hn-recall-cs25-"))
    item.update({
        "exam_event_verified": verified_event,
        "item_text_level": "task_recall",
        "form_confidence": "medium",
        "content_confidence": "medium" if verified_event else "low",
    })
    return item


def compact(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def validate(question):
    qid = str(question.get("id") or "")
    errors = []
    required = (
        "id", "source", "type", "chapter", "stem", "answer", "explanation",
        "subject", "source_chapter", "adaptation_note", "source_url",
        "source_title", "source_item", "evidence_level", "review_status", "version",
        "item_text_level", "form_confidence", "content_confidence",
    )
    for field in required:
        if question.get(field) in (None, "", [], {}):
            errors.append(f"{qid or '<无ID>'}: 缺少{field}")
    if not qid.startswith(PREFIX) or question.get("source") != SOURCE:
        errors.append(f"{qid}: ID或来源无效")
    if not str(question.get("source_url") or "").startswith("https://www.xiaohongshu.com/explore/"):
        errors.append(f"{qid}: 回忆来源地址无效")
    if question.get("origin_verified") is not False or question.get("answer_reviewed") is not True:
        errors.append(f"{qid}: 核验状态无效")
    if question.get("exam_event_verified") not in {True, False}:
        errors.append(f"{qid}: 考试事件核验状态无效")
    qtype = question.get("type")
    options = question.get("options")
    if qtype in {"单选", "多选"} and (not isinstance(options, dict) or len(options) < 2):
        errors.append(f"{qid}: 选择题选项无效")
    if qtype in {"判断", "填空", "简答"} and options not in ({}, None):
        errors.append(f"{qid}: 非选择题不应有选项")
    if qtype == "简答":
        rubric = question.get("rubric")
        if not isinstance(rubric, list) or not rubric:
            errors.append(f"{qid}: 简答题缺少核对要点")
        elif sum(item.get("points", 0) for item in rubric) != question.get("max_score"):
            errors.append(f"{qid}: 核对要点与满分不符")
    return errors


def build(existing, candidates):
    errors = []
    ids = set()
    for question in candidates:
        errors.extend(validate(question))
        qid = question.get("id")
        if qid in ids:
            errors.append(f"重复ID：{qid}")
        ids.add(qid)

    base = [question for question in existing if not str(question.get("id") or "").startswith(PREFIX)]
    exact = {(question.get("subject"), compact(question.get("stem"))): question.get("id") for question in base}
    for question in candidates:
        key = (question.get("subject"), compact(question.get("stem")))
        if key in exact:
            errors.append(f"题干重复：{question.get('id')} / {exact[key]}")
    if errors:
        raise ValueError("湖南笔试回忆改编题校验失败：\n" + "\n".join(errors))

    derived = {
        str(question.get("id") or ""): {key: question[key] for key in DERIVED_FIELDS if key in question}
        for question in existing
    }
    result = []
    for question in base + candidates:
        saved = dict(derived.get(str(question.get("id") or ""), {}))
        if question.get("topic_source") == "manual" and saved.get("topic_id") != question.get("topic_id"):
            for field in ("topic_id", "topic_title", "chapter_id", "required_depth", "topic_order"):
                saved.pop(field, None)
        result.append({**question, **saved})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    existing = json.loads(QUESTION_JSON.read_text(encoding="utf-8"))
    candidates = [add_confidence(question) for question in json.loads(STAGING.read_text(encoding="utf-8"))]
    merged = apply_reviews(build(existing, apply_reviews(candidates)))
    if args.check:
        if merged != existing:
            raise SystemExit("湖南笔试回忆改编题与questions.json不同步")
        print(f"湖南笔试回忆改编题已同步：{len(candidates)}题")
        return
    QUESTION_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"湖南笔试回忆改编题合并完成：{len(candidates)}题，总题量{len(merged)}")


if __name__ == "__main__":
    main()
