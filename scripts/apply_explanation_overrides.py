"""Apply reviewed explanation replacements for legacy base questions."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from question_reviews import apply_reviews, load_removals


ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"
STAGING = ROOT / "staging"
GENERIC = re.compile(r"(?:符合题意|题干要求相符).{0,20}故选", re.S)


def load_overrides() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(STAGING.glob("explanation_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path.name} 必须是JSON数组")
        for item in payload:
            question_id = str(item.get("id") or "")
            explanation = str(item.get("explanation") or "").strip()
            if not question_id or question_id in result:
                raise ValueError(f"解析覆盖ID为空或重复：{question_id}")
            if len(explanation) < 40 or GENERIC.search(explanation):
                raise ValueError(f"解析仍过短或模板化：{question_id}")
            result[question_id] = explanation
    return result


def build(questions: list[dict], overrides: dict[str, str]) -> list[dict]:
    known_ids = {str(question.get("id") or "") for question in questions}
    missing = sorted(set(overrides) - known_ids - load_removals())
    if missing:
        raise ValueError("解析覆盖题号不存在：" + ", ".join(missing))
    edits = json.loads((STAGING / "question_text_edits.json").read_text(encoding="utf-8"))
    edit_ids = [item["id"] for item in edits]
    if len(edit_ids) != len(set(edit_ids)) or set(edit_ids) - known_ids - load_removals():
        raise ValueError("题干选项修订包含重复或不存在的ID")
    if any(set(item) - {"id", "stem", "options"} for item in edits):
        raise ValueError("题干选项修订只允许id、stem和options字段")
    by_id = {item["id"]: item for item in edits}
    return apply_reviews([
        {**question, **by_id.get(question["id"], {}), **({"explanation": overrides[question["id"]]} if question["id"] in overrides else {})}
        for question in questions
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    questions = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
    overrides = load_overrides()
    updated = build(questions, overrides)
    if args.check:
        if updated != questions:
            raise SystemExit("题目解析与人工复核结果不同步")
        print(f"题目解析已同步：{len(overrides)}题")
        return
    QUESTION_FILE.write_text(json.dumps(updated, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"题目解析已更新：{len(overrides)}题")


if __name__ == "__main__":
    main()
