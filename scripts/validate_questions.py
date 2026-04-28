import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"
CHOICE_TYPES = {"单选", "多选"}
JUDGE_ANSWERS = {"正确", "错误"}


def main():
    qs = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
    errors = []

    ids = [q.get("id") for q in qs]
    for qid, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate id: {qid}")

    for index, q in enumerate(qs, 1):
        qid = q.get("id") or f"#{index}"
        qtype = q.get("type")
        answer = str(q.get("answer") or "")
        options = q.get("options") or {}

        for field in ("id", "source", "type", "stem", "subject"):
            if not q.get(field):
                errors.append(f"{qid}: missing {field}")

        if qtype in CHOICE_TYPES:
            if qtype == "单选" and len(answer) != 1:
                errors.append(f"{qid}: single-choice answer should be one letter: {answer}")
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

    print(f"questions: {len(qs)}")
    print(f"errors: {len(errors)}")
    for err in errors[:80]:
        print(err)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
