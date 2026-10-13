import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from enrich_question_metadata import (
    ABILITY_VALUES,
    DIFFICULTY_VALUES,
    KNOWLEDGE_POINT_VALUES,
)

ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"
CHOICE_TYPES = {"单选", "多选"}
JUDGE_ANSWERS = {"正确", "错误"}
UNIVERSITY_PREFIXES = ("ua-", "uc-", "ue-")
APPLIED_PREFIXES = ("ap-", "sp-")
NATIONAL_PREFIX = "nw-national-"
NATIONAL_SOURCES = {
    source["url"] for source in json.loads((ROOT / "network-exam-sources.json").read_text(encoding="utf-8"))["sources"]
    if source["kind"] in {"高校官方公开期末卷", "高校官方期末答案及题卷索引", "高校官方期末考试分析", "社区收录期末卷", "事业单位试题整理稿", "事业单位回忆材料"}
}
LEARNING_MAP = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
COURSE_BY_SUBJECT = {
    subject: course
    for course in LEARNING_MAP["courses"]
    for subject in course.get("subjects", [course["subject"]])
}
TOPICS = {
    topic["topic_id"]: topic
    for course in LEARNING_MAP["courses"]
    for topic in course.get("topics", [])
}
TOPIC_ORDER = {
    topic["topic_id"]: index
    for course in LEARNING_MAP["courses"]
    for index, topic in enumerate(course.get("topics", []))
}


def normalized_stem(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"^\s*(?:第?\d+[.、：)]|[一二三四五六七八九十]+[、.)])\s*", "", text)
    text = re.sub(r"[（(]\s*[）)]\s*[。.]?$", "", text)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=QUESTION_FILE)
    parser.add_argument("--js", type=Path)
    parser.add_argument("--allow-missing-js", action="store_true")
    args = parser.parse_args()
    qs = json.loads(args.questions.read_text(encoding="utf-8"))
    errors = []

    if args.js is None:
        pass
    elif args.js.is_file():
        js_text = args.js.read_text(encoding="utf-8").strip()
        prefix = "window.QUESTIONS="
        if not js_text.startswith(prefix) or not js_text.endswith(";"):
            errors.append("questions.js: invalid wrapper")
        else:
            try:
                js_questions = json.loads(js_text[len(prefix):-1])
                if js_questions != qs:
                    errors.append("questions.js is not synchronized with questions.json")
            except json.JSONDecodeError as error:
                errors.append(f"questions.js: invalid JSON payload: {error}")
    elif not args.allow_missing_js:
        errors.append(f"missing generated question bundle: {args.js}")

    ids = [q.get("id") for q in qs]
    for qid, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate id: {qid}")

    normalized = {}
    for q in qs:
        key = (str(q.get("subject") or ""), normalized_stem(q.get("stem")))
        if key[1] and key in normalized:
            errors.append(
                f"duplicate normalized stem in {key[0]}: "
                f"{normalized[key].get('id')} / {q.get('id')}"
            )
        else:
            normalized[key] = q

    for index, q in enumerate(qs, 1):
        qid = q.get("id") or f"#{index}"
        qtype = q.get("type")
        if q.get("subject") == "教学论":
            errors.append(f"{qid}: 教师方向已移除，不应重新加入现行题库")
        answer = str(q.get("answer") or "")
        options = q.get("options") or {}

        for field in ("id", "source", "type", "stem", "subject"):
            if not q.get(field):
                errors.append(f"{qid}: missing {field}")

        if qtype in CHOICE_TYPES:
            if not isinstance(options, dict):
                errors.append(f"{qid}: options should be an object")
                options = {}
            for key, value in options.items():
                if not isinstance(key, str) or not re.fullmatch(r"[A-Z]", key):
                    errors.append(f"{qid}: invalid option key: {key!r}")
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{qid}: empty option value: {key!r}")
            if qtype == "单选" and len(answer) != 1:
                errors.append(f"{qid}: single-choice answer should be one letter: {answer}")
            if not re.fullmatch(r"[A-Z]+", answer) or len(set(answer)) != len(answer):
                errors.append(f"{qid}: invalid or duplicated choice answer: {answer}")
            if len(options) < 2:
                errors.append(f"{qid}: too few options")
            for letter in answer:
                if letter not in options:
                    errors.append(f"{qid}: answer {letter} missing from options")
        elif qtype == "判断":
            if answer not in JUDGE_ANSWERS:
                errors.append(f"{qid}: bad judge answer: {answer}")
        elif qtype in {"填空", "简答"}:
            if not answer:
                errors.append(f"{qid}: {qtype} question has empty answer")
            if qtype == "简答" and options not in ({}, None):
                errors.append(f"{qid}: short-answer options should be empty")
        else:
            errors.append(f"{qid}: unknown type: {qtype}")
        if not str(q.get("explanation") or "").strip():
            errors.append(f"{qid}: missing explanation")

        knowledge_point = str(q.get("knowledge_point") or "").strip()
        ability = str(q.get("ability") or "").strip()
        difficulty = str(q.get("difficulty") or "").strip()
        if not knowledge_point:
            errors.append(f"{qid}: missing knowledge_point")
        elif knowledge_point not in KNOWLEDGE_POINT_VALUES:
            errors.append(f"{qid}: invalid knowledge_point: {knowledge_point}")
        if not ability:
            errors.append(f"{qid}: missing ability")
        elif ability not in ABILITY_VALUES:
            errors.append(f"{qid}: invalid ability: {ability}")
        if not difficulty:
            errors.append(f"{qid}: missing difficulty")
        elif difficulty not in DIFFICULTY_VALUES:
            errors.append(f"{qid}: invalid difficulty: {difficulty}")
        if qtype == "简答":
            rubric = q.get("rubric")
            if not isinstance(rubric, list) or not rubric:
                errors.append(f"{qid}: short answer requires rubric")
            elif any(not item.get("criterion") or not isinstance(item.get("points"), int) or item["points"] <= 0 for item in rubric):
                errors.append(f"{qid}: invalid short-answer rubric")
            elif sum(item["points"] for item in rubric) != q.get("max_score"):
                errors.append(f"{qid}: rubric points do not match max_score")
        if ability == "直接计算" and qtype in {"填空", "简答"}:
            rubric = q.get("rubric")
            if not isinstance(rubric, list) or not rubric or sum(item.get("points", 0) for item in rubric) != q.get("max_score"):
                errors.append(f"{qid}: calculation requires a valid rubric")

        if str(qid).startswith(UNIVERSITY_PREFIXES):
            if q.get("source") != "大学期末改编":
                errors.append(f"{qid}: university adaptation has invalid source")
            for field in ("source_chapter", "source_url", "source_title", "adaptation_note"):
                if not str(q.get(field) or "").strip():
                    errors.append(f"{qid}: missing provenance field {field}")
            if not str(q.get("source_url") or "").startswith("https://"):
                errors.append(f"{qid}: source_url should use https")
        if str(qid).startswith(APPLIED_PREFIXES):
            if q.get("source") != "高校试题提炼":
                errors.append(f"{qid}: applied question has invalid source")
            for field in ("source_chapter", "source_url", "source_title", "adaptation_note"):
                if not str(q.get(field) or "").strip():
                    errors.append(f"{qid}: missing provenance field {field}")
            if not str(q.get("source_url") or "").startswith("https://"):
                errors.append(f"{qid}: source_url should use https")
        if str(qid).startswith(NATIONAL_PREFIX):
            if q.get("source") != "全国试题提炼":
                errors.append(f"{qid}: invalid national source label")
            for field in ("source_chapter", "source_url", "source_title", "adaptation_note"):
                if not str(q.get(field) or "").strip():
                    errors.append(f"{qid}: missing provenance field {field}")
            if q.get("source_url") not in NATIONAL_SOURCES:
                errors.append(f"{qid}: source_url does not match a reviewed exam material")
            for field in ("source_id", "source_item", "evidence_level", "review_status", "version"):
                if q.get(field) in (None, ""):
                    errors.append(f"{qid}: missing structured provenance field {field}")
            if q.get("origin_verified") not in (True, False) or q.get("answer_reviewed") is not True:
                errors.append(f"{qid}: invalid review flags")
            accepted = q.get("accepted_answers")
            if accepted is not None and (not isinstance(accepted, list) or not accepted or any(not str(value).strip() for value in accepted)):
                errors.append(f"{qid}: invalid accepted_answers")
        if q.get("subject") in COURSE_BY_SUBJECT:
            topic = TOPICS.get(q.get("topic_id"))
            if not topic:
                errors.append(f"{qid}: missing or invalid topic_id")
            elif q.get("topic_title") != topic["title"] or q.get("chapter_id") != topic["chapter_id"]:
                errors.append(f"{qid}: topic metadata does not match learning-map.json")
            elif q.get("topic_order") != TOPIC_ORDER.get(topic["topic_id"]):
                errors.append(f"{qid}: topic order does not match learning-map.json")

    for course in LEARNING_MAP["courses"]:
        subjects = set(course.get("subjects", [course["subject"]]))
        covered_topics = {question.get("topic_id") for question in qs if question.get("subject") in subjects}
        required_topics = {topic["topic_id"] for topic in course["topics"]}
        missing_topics = sorted(required_topics - covered_topics)
        if missing_topics:
            errors.append(f"{course['course_name']}知识点没有练习：" + ", ".join(missing_topics))

    print(f"questions: {len(qs)}")
    print(f"errors: {len(errors)}")
    for err in errors[:80]:
        print(err)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
