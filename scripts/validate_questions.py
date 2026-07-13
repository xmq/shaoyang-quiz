import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"
QUESTION_JS_FILE = ROOT / "questions.js"
CHOICE_TYPES = {"单选", "多选"}
JUDGE_ANSWERS = {"正确", "错误"}
UNIVERSITY_PREFIXES = ("ua-", "uc-", "ue-")


def normalized_stem(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"^\s*(?:第?\d+[.、：)]|[一二三四五六七八九十]+[、.)])\s*", "", text)
    text = re.sub(r"[（(]\s*[）)]\s*[。.]?$", "", text)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def main():
    qs = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
    errors = []

    js_text = QUESTION_JS_FILE.read_text(encoding="utf-8").strip()
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
        elif qtype == "填空":
            if not answer:
                errors.append(f"{qid}: blank question has empty answer")
        else:
            errors.append(f"{qid}: unknown type: {qtype}")
        if not str(q.get("explanation") or "").strip():
            errors.append(f"{qid}: missing explanation")

        if str(qid).startswith(UNIVERSITY_PREFIXES):
            if q.get("source") != "大学期末改编":
                errors.append(f"{qid}: university adaptation has invalid source")
            for field in ("source_chapter", "source_url", "source_title", "adaptation_note"):
                if not str(q.get(field) or "").strip():
                    errors.append(f"{qid}: missing provenance field {field}")
            if not str(q.get("source_url") or "").startswith("https://"):
                errors.append(f"{qid}: source_url should use https")

    print(f"questions: {len(qs)}")
    print(f"errors: {len(errors)}")
    for err in errors[:80]:
        print(err)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
