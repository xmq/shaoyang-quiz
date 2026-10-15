"""Merge the reviewed questions that fill empty course topics."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from question_reviews import apply_reviews, load_gap_questions

ROOT = Path(__file__).resolve().parents[1]
QUESTION_JSON = ROOT / "questions.json"
STAGING = ROOT / "staging" / "course_gap_questions.json"
PREFIX = "gap-"
DERIVED_FIELDS = ("knowledge_point", "ability", "difficulty", "topic_id", "topic_title", "chapter_id", "required_depth", "topic_order", "rubric", "max_score", "rubric_source")
GROUP_PREFIXES = ("ap-", "sp-", "ua-", "uc-", "ue-", "hn-recall-")


def compact(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def validate(question):
    qid = str(question.get("id") or "")
    errors = []
    for field in ("id", "source", "type", "chapter", "stem", "answer", "explanation", "subject", "source_chapter", "adaptation_note"):
        if not str(question.get(field) or "").strip():
            errors.append(f"{qid or '<无ID>'}: 缺少{field}")
    if not qid.startswith(PREFIX) or question.get("source") != "课程缺口补充":
        errors.append(f"{qid}: ID或来源无效")
    qtype = question.get("type")
    options = question.get("options")
    if qtype in {"单选", "多选"} and (not isinstance(options, dict) or len(options) < 2):
        errors.append(f"{qid}: 选择题选项无效")
    if qtype in {"填空", "简答"} and options not in ({}, None):
        errors.append(f"{qid}: 主观题不应有选项")
    rubric = question.get("rubric")
    if qtype in {"填空", "简答"}:
        if not isinstance(rubric, list) or not rubric:
            errors.append(f"{qid}: 缺少评分点")
        elif sum(item.get("points", 0) for item in rubric) != question.get("max_score"):
            errors.append(f"{qid}: 评分点与满分不符")
    return errors


def build(existing, candidates):
    errors = []
    ids = set()
    for question in candidates:
        errors.extend(validate(question))
        if question.get("id") in ids:
            errors.append(f"重复ID：{question.get('id')}")
        ids.add(question.get("id"))
    base_without_gap = [question for question in existing if not str(question.get("id") or "").startswith(PREFIX)]
    exact = {(question.get("subject"), compact(question.get("stem"))): question.get("id") for question in base_without_gap}
    for question in candidates:
        key = (question.get("subject"), compact(question.get("stem")))
        if key in exact:
            errors.append(f"题干重复：{question.get('id')} / {exact[key]}")
    if errors:
        raise ValueError("课程缺口题校验失败：\n" + "\n".join(errors))

    derived = {
        str(question.get("id") or ""): {key: question[key] for key in DERIVED_FIELDS if key in question}
        for question in existing
    }
    grouped = [question for question in base_without_gap if str(question.get("id") or "").startswith(GROUP_PREFIXES)]
    base = [question for question in base_without_gap if question not in grouped]
    result = []
    for question in base + candidates + grouped:
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
    candidates = load_gap_questions()
    merged = apply_reviews(build(existing, candidates))
    if args.check:
        if merged != existing:
            raise SystemExit("课程缺口题与questions.json不同步")
        print(f"课程缺口题已同步：{len(candidates)}题")
        return
    QUESTION_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"课程缺口题合并完成：{len(candidates)}题，总题量{len(merged)}")


if __name__ == "__main__":
    main()
