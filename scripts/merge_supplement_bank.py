"""Validate, deduplicate and merge the second-round thin-subject supplements."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_JSON = ROOT / "questions.json"
PREFIX = "sp-"
SOURCE = "高校试题提炼"
STAGING_SPECS = {
    ROOT / "staging" / "supplement_core_thin.json": {
        "计算机组成原理": 46,
        "算法与数据结构": 34,
        "软件工程": 31,
    },
    ROOT / "staging" / "supplement_electronics_practical.json": {
        "电路分析与电工技术": 30,
        "模拟电子技术": 30,
        "数字电子技术": 30,
        "通信原理与高频电子线路": 30,
    },
}
CHOICE_TYPES = {"单选", "多选"}
OTHER_TYPES = {"判断", "填空", "简答"}


def compact_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"^\s*(?:第?\d+[.、)）]|[一二三四五六七八九十]+[、.])\s*", "", text)
    text = re.sub(r"[（(]\s*[）)]\s*[。.]?$", "", text)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def grams(text: str, size: int = 3) -> set[str]:
    if len(text) <= size:
        return {text}
    return {text[index:index + size] for index in range(len(text) - size + 1)}


def similarity(left: dict, right: dict) -> tuple[float, float]:
    a = compact_text(left.get("stem"))
    b = compact_text(right.get("stem"))
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    ga, gb = grams(a), grams(b)
    jaccard = len(ga & gb) / max(1, len(ga | gb))
    return ratio, jaccard


def validate_question(question: dict, origin: str) -> list[str]:
    errors: list[str] = []
    qid = str(question.get("id") or "<无ID>")
    required = (
        "id", "source", "type", "chapter", "stem", "answer", "explanation", "subject",
        "source_chapter", "source_url", "source_title", "adaptation_note",
    )
    for field in required:
        if not str(question.get(field) or "").strip():
            errors.append(f"{origin}/{qid}: 缺少 {field}")
    if not qid.startswith(PREFIX):
        errors.append(f"{origin}/{qid}: ID必须使用 {PREFIX} 前缀")
    if question.get("source") != SOURCE:
        errors.append(f"{origin}/{qid}: source必须为{SOURCE}")
    if not str(question.get("source_url") or "").startswith("https://"):
        errors.append(f"{origin}/{qid}: source_url必须使用https")
    if len(str(question.get("stem") or "").strip()) < 9:
        errors.append(f"{origin}/{qid}: 题干过短")
    if len(str(question.get("explanation") or "").strip()) < 18:
        errors.append(f"{origin}/{qid}: 解析过短")

    qtype = question.get("type")
    answer = str(question.get("answer") or "")
    options = question.get("options")
    if qtype in CHOICE_TYPES:
        if not isinstance(options, dict) or len(options) < 2:
            errors.append(f"{origin}/{qid}: 选择题选项不足")
            options = {}
        if qtype == "单选" and not re.fullmatch(r"[A-Z]", answer):
            errors.append(f"{origin}/{qid}: 单选答案必须是单个字母")
        if qtype == "多选" and (not re.fullmatch(r"[A-Z]+", answer) or len(answer) < 2):
            errors.append(f"{origin}/{qid}: 多选答案格式错误")
        if len(set(answer)) != len(answer) or any(letter not in options for letter in answer):
            errors.append(f"{origin}/{qid}: 答案与选项不匹配")
    elif qtype in OTHER_TYPES:
        if options not in ({}, None):
            errors.append(f"{origin}/{qid}: {qtype}题 options应为空对象")
        if qtype == "判断" and answer not in {"正确", "错误"}:
            errors.append(f"{origin}/{qid}: 判断答案格式错误")
        if qtype == "简答" and len(answer.strip()) < 18:
            errors.append(f"{origin}/{qid}: 简答参考答案过短")
    else:
        errors.append(f"{origin}/{qid}: 不支持的题型 {qtype}")
    return errors


def load_candidates() -> list[dict]:
    errors: list[str] = []
    candidates: list[dict] = []
    seen_ids: set[str] = set()
    for path, expected in STAGING_SPECS.items():
        if not path.is_file():
            errors.append(f"缺少暂存题库：{path.name}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            errors.append(f"{path.name}: 必须是JSON数组")
            continue
        counts = Counter()
        type_counts: dict[str, Counter] = {subject: Counter() for subject in expected}
        for question in payload:
            if not isinstance(question, dict):
                errors.append(f"{path.name}: 存在非对象题目")
                continue
            errors.extend(validate_question(question, path.name))
            qid = str(question.get("id") or "")
            subject = str(question.get("subject") or "")
            if qid in seen_ids:
                errors.append(f"暂存题库重复ID：{qid}")
            seen_ids.add(qid)
            if subject not in expected:
                errors.append(f"{path.name}/{qid}: 科目不属于本分组")
            counts[subject] += 1
            type_counts.setdefault(subject, Counter())[question.get("type")] += 1
            candidates.append(question)
        for subject, expected_count in expected.items():
            if counts[subject] != expected_count:
                errors.append(f"{path.name}: {subject}应为{expected_count}题，实际{counts[subject]}题")
            if type_counts[subject]["简答"] < 5:
                errors.append(f"{path.name}: {subject}至少应含5道简答")
            if type_counts[subject]["判断"] < 5:
                errors.append(f"{path.name}: {subject}至少应含5道判断")
    if errors:
        raise ValueError("补充题库校验失败：\n" + "\n".join(errors[:150]))
    return candidates


def build_merged(existing: list[dict], candidates: list[dict]) -> list[dict]:
    without_supplement = [q for q in existing if not str(q.get("id") or "").startswith(PREFIX)]
    university = [q for q in without_supplement if str(q.get("id") or "").startswith(("ua-", "uc-", "ue-"))]
    applied = [q for q in without_supplement if str(q.get("id") or "").startswith("ap-")]
    base = [q for q in without_supplement if q not in university and q not in applied]
    comparison_pool = base + applied + university
    exact = {(str(q.get("subject") or ""), compact_text(q.get("stem"))): q for q in comparison_pool}
    accepted: list[dict] = []
    errors: list[str] = []
    for candidate in candidates:
        key = (str(candidate.get("subject") or ""), compact_text(candidate.get("stem")))
        if key in exact:
            errors.append(f"题干规范化重复：{candidate['id']} / {exact[key].get('id')}")
            continue
        for other in comparison_pool + accepted:
            if candidate.get("subject") != other.get("subject"):
                continue
            ratio, jaccard = similarity(candidate, other)
            if ratio >= .965 or (ratio >= .92 and jaccard >= .84):
                errors.append(
                    f"题干近似重复：{candidate['id']} / {other.get('id')} "
                    f"(ratio={ratio:.3f}, jaccard={jaccard:.3f})"
                )
                break
        else:
            accepted.append(candidate)
            exact[key] = candidate
    if errors:
        raise ValueError("补充题库去重失败：\n" + "\n".join(errors[:150]))
    return base + applied + accepted + university


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    existing = json.loads(QUESTION_JSON.read_text(encoding="utf-8"))
    candidates = load_candidates()
    merged = build_merged(existing, candidates)
    if args.check:
        if merged != existing:
            print(f"补充题库未同步：候选{len(candidates)}，合并后{len(merged)}，当前{len(existing)}")
            return 1
        print(f"补充题库已同步：候选{len(candidates)}，总题量{len(existing)}")
        return 0
    QUESTION_JSON.write_text(
        json.dumps(merged, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"补充题库合并完成：候选{len(candidates)}，总题量{len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
