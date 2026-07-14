"""Validate, deduplicate and merge application-oriented question candidates."""

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
SOURCE = "高校试题提炼"
PREFIX = "ap-"
EXPECTED_PER_SUBJECT = 6
STAGING_SPECS = {
    ROOT / "staging" / "applied_core_computer.json": {
        "操作系统", "计算机组成原理", "算法与数据结构", "数据库", "编程语言", "软件工程",
    },
    ROOT / "staging" / "applied_network_application.json": {
        "办公软件", "教学论", "多媒体", "计算机网络", "信息安全",
    },
    ROOT / "staging" / "applied_electronics.json": {
        "电路分析与电工技术", "模拟电子技术", "数字电子技术", "通信原理与高频电子线路",
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
    if len(str(question.get("stem") or "").strip()) < 10:
        errors.append(f"{origin}/{qid}: 题干过短")
    if len(str(question.get("explanation") or "").strip()) < 20:
        errors.append(f"{origin}/{qid}: 解析过短，应说明步骤、机制或边界")

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
            errors.append(f"{origin}/{qid}: {qtype}题 options 应为空对象")
        if qtype == "判断" and answer not in {"正确", "错误"}:
            errors.append(f"{origin}/{qid}: 判断答案必须为正确或错误")
        if qtype == "简答" and len(answer.strip()) < 18:
            errors.append(f"{origin}/{qid}: 简答参考得分点过短")
    else:
        errors.append(f"{origin}/{qid}: 不支持的题型 {qtype}")
    return errors


def load_candidates() -> list[dict]:
    errors: list[str] = []
    candidates: list[dict] = []
    seen_ids: set[str] = set()
    for path, allowed_subjects in STAGING_SPECS.items():
        if not path.is_file():
            errors.append(f"缺少暂存题库：{path.name}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            errors.append(f"{path.name}: 必须是JSON数组")
            continue
        counts = Counter()
        type_counts: dict[str, Counter] = {subject: Counter() for subject in allowed_subjects}
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
            if subject not in allowed_subjects:
                errors.append(f"{path.name}/{qid}: 科目不属于本分组")
            counts[subject] += 1
            type_counts.setdefault(subject, Counter())[question.get("type")] += 1
            candidates.append(question)
        for subject in sorted(allowed_subjects):
            if counts[subject] != EXPECTED_PER_SUBJECT:
                errors.append(f"{path.name}: {subject}应为{EXPECTED_PER_SUBJECT}题，实际{counts[subject]}题")
            # 简答题由知识形态决定，不能为了凑固定配额把普通概念强行改成简答。
            # 应用补充库只约束上限，保证客观题仍是主体。
            if type_counts[subject]["简答"] > 2:
                errors.append(f"{path.name}: {subject}简答题不应超过2道")
    if errors:
        raise ValueError("暂存题库校验失败：\n" + "\n".join(errors[:120]))
    return candidates


def build_merged(existing: list[dict], candidates: list[dict]) -> list[dict]:
    without_applied = [question for question in existing if not str(question.get("id") or "").startswith(PREFIX)]
    university = [
        question for question in without_applied
        if str(question.get("id") or "").startswith(("ua-", "uc-", "ue-"))
    ]
    supplement = [
        question for question in without_applied
        if str(question.get("id") or "").startswith("sp-")
    ]
    base = [question for question in without_applied if question not in university and question not in supplement]
    comparison_pool = base + supplement + university
    accepted: list[dict] = []
    exact = {
        (str(question.get("subject") or ""), compact_text(question.get("stem"))): question
        for question in comparison_pool
    }
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
            if ratio >= 0.975 or (ratio >= 0.94 and jaccard >= 0.88):
                errors.append(
                    f"题干近似重复：{candidate['id']} / {other.get('id')} "
                    f"(ratio={ratio:.3f}, jaccard={jaccard:.3f})"
                )
                break
        else:
            accepted.append(candidate)
            exact[key] = candidate
    if errors:
        raise ValueError("应用题去重失败：\n" + "\n".join(errors[:120]))
    # Keep both reproducible merge pipelines stable: application questions sit
    # before the managed university-final groups, which their merger appends.
    return base + accepted + supplement + university


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="仅校验questions.json是否与暂存题库同步")
    args = parser.parse_args()
    existing = json.loads(QUESTION_JSON.read_text(encoding="utf-8"))
    candidates = load_candidates()
    merged = build_merged(existing, candidates)
    if args.check:
        if merged != existing:
            print(f"应用题库未同步：候选{len(candidates)}，合并后{len(merged)}，当前{len(existing)}")
            return 1
        print(f"应用题库已同步：候选{len(candidates)}，总题量{len(existing)}")
        return 0
    QUESTION_JSON.write_text(
        json.dumps(merged, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"应用题库合并完成：候选{len(candidates)}，入库{len(candidates)}，总题量{len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
