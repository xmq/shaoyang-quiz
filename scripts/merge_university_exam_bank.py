"""Validate, deduplicate and merge university-final adaptations into the bank."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from question_reviews import apply_reviews


ROOT = Path(__file__).resolve().parents[1]
QUESTION_JSON = ROOT / "questions.json"
STAGING_SPECS = {
    ROOT / "staging" / "university_applied.json": (
        "ua-", {"办公软件", "多媒体", "编程语言", "信息安全"},
    ),
    ROOT / "staging" / "university_corecs.json": (
        "uc-", {"操作系统", "数据库", "算法与数据结构", "计算机组成原理", "计算机网络", "软件工程"},
    ),
    ROOT / "staging" / "university_electronics.json": (
        "ue-", {"电路分析与电工技术", "模拟电子技术", "数字电子技术", "通信原理与高频电子线路"},
    ),
}
STAGING_FILES = tuple(STAGING_SPECS)
PROGRAMMING_REMOVAL_FILE = ROOT / "staging" / "programming_vb_remove_ids.json"
MANAGED_PREFIXES = ("ua-", "uc-", "ue-")
DERIVED_METADATA_FIELDS = ("topic_id", "topic_title", "chapter_id", "required_depth", "topic_order", "rubric", "max_score", "rubric_source")
CHOICE_TYPES = {"单选", "多选"}
JUDGE_ANSWERS = {"正确", "错误"}


def compact_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"^\s*(?:第?\d+[.、)）]|[一二三四五六七八九十]+[、.])\s*", "", text)
    text = re.sub(r"[（(]\s*[）)]\s*[。.]?$", "", text)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def number_tokens(value: object) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return tuple(re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text))


def option_signature(question: dict) -> str:
    options = question.get("options") or {}
    return "|".join(compact_text(value) for _, value in sorted(options.items()))


def grams(text: str, size: int = 3) -> set[str]:
    if len(text) <= size:
        return {text}
    return {text[index:index + size] for index in range(len(text) - size + 1)}


def similarity(left: dict, right: dict) -> tuple[float, float, float]:
    a = compact_text(left.get("stem"))
    b = compact_text(right.get("stem"))
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    ga, gb = grams(a), grams(b)
    jaccard = len(ga & gb) / max(1, len(ga | gb))
    oa, ob = option_signature(left), option_signature(right)
    option_ratio = SequenceMatcher(None, oa, ob, autojunk=False).ratio() if oa or ob else 1.0
    return ratio, jaccard, option_ratio


def is_near_duplicate(left: dict, right: dict) -> tuple[bool, tuple[float, float, float]]:
    if left.get("subject") != right.get("subject"):
        return False, (0.0, 0.0, 0.0)
    a = compact_text(left.get("stem"))
    b = compact_text(right.get("stem"))
    if min(len(a), len(b)) < 16 or number_tokens(left.get("stem")) != number_tokens(right.get("stem")):
        return False, (0.0, 0.0, 0.0)
    scores = similarity(left, right)
    ratio, jaccard, option_ratio = scores
    duplicate = ratio >= 0.975 or (ratio >= 0.94 and jaccard >= 0.88 and option_ratio >= 0.86)
    return duplicate, scores


def validate_question(question: dict, origin: str) -> list[str]:
    errors = []
    qid = str(question.get("id") or "<无ID>")
    for field in (
        "id", "source", "type", "chapter", "stem", "answer", "explanation",
        "subject", "source_chapter", "source_url", "source_title", "adaptation_note",
    ):
        if not str(question.get(field) or "").strip():
            errors.append(f"{origin}/{qid}: 缺少 {field}")
    if question.get("source") != "大学期末改编":
        errors.append(f"{origin}/{qid}: source 必须为大学期末改编")
    if not qid.startswith(MANAGED_PREFIXES):
        errors.append(f"{origin}/{qid}: ID前缀必须是 ua-/uc-/ue-")
    if not str(question.get("source_url") or "").startswith("https://"):
        errors.append(f"{origin}/{qid}: source_url 必须是 https 地址")

    qtype = question.get("type")
    answer = str(question.get("answer") or "")
    options = question.get("options") or {}
    if qtype in CHOICE_TYPES:
        if not isinstance(options, dict) or len(options) < 2:
            errors.append(f"{origin}/{qid}: 选择题选项不足")
        if not re.fullmatch(r"[A-Z]+", answer):
            errors.append(f"{origin}/{qid}: 选择题答案格式错误")
        if qtype == "单选" and len(answer) != 1:
            errors.append(f"{origin}/{qid}: 单选答案只能有一个字母")
        if len(set(answer)) != len(answer) or any(letter not in options for letter in answer):
            errors.append(f"{origin}/{qid}: 答案与选项不匹配")
    elif qtype == "判断":
        if answer not in JUDGE_ANSWERS:
            errors.append(f"{origin}/{qid}: 判断题答案必须为正确或错误")
        if options not in ({}, None):
            errors.append(f"{origin}/{qid}: 判断题 options 应为空对象")
    else:
        errors.append(f"{origin}/{qid}: 新增题只允许单选、多选、判断")
    if len(str(question.get("explanation") or "")) < 18:
        errors.append(f"{origin}/{qid}: 解析过短，至少应说明原理或步骤")
    return errors


def load_staging() -> list[dict]:
    missing = [path.name for path in STAGING_FILES if not path.is_file()]
    if missing:
        raise FileNotFoundError("缺少暂存题库：" + "、".join(missing))
    questions = []
    errors = []
    ids = set()
    for path in STAGING_FILES:
        required_prefix, allowed_subjects = STAGING_SPECS[path]
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path.name} 必须是JSON数组")
        for question in payload:
            if not isinstance(question, dict):
                errors.append(f"{path.name}: 存在非对象题目")
                continue
            errors.extend(validate_question(question, path.name))
            qid = question.get("id")
            if not str(qid or "").startswith(required_prefix):
                errors.append(f"{path.name}/{qid}: ID 必须使用 {required_prefix} 前缀")
            if question.get("subject") not in allowed_subjects:
                errors.append(f"{path.name}/{qid}: 科目不属于本分组")
            if qid in ids:
                errors.append(f"暂存题库重复ID：{qid}")
            ids.add(qid)
            questions.append(question)
        counts = Counter(q.get("subject") for q in payload if isinstance(q, dict))
        for subject in sorted(allowed_subjects):
            if counts[subject] != 15:
                errors.append(f"{path.name}: {subject} 应为15题，实际{counts[subject]}题")
            urls = {
                q.get("source_url") for q in payload
                if isinstance(q, dict) and q.get("subject") == subject and q.get("source_url")
            }
            if len(urls) < 2:
                errors.append(f"{path.name}: {subject} 至少需要2个不同公开来源，实际{len(urls)}个")
    if errors:
        raise ValueError("暂存题库校验失败：\n" + "\n".join(errors[:100]))
    return questions


def load_programming_removals(questions: list[dict]) -> set[str]:
    if not PROGRAMMING_REMOVAL_FILE.is_file():
        raise FileNotFoundError(f"缺少范围校准清单：{PROGRAMMING_REMOVAL_FILE.name}")
    payload = json.loads(PROGRAMMING_REMOVAL_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(qid, str) for qid in payload):
        raise ValueError(f"{PROGRAMMING_REMOVAL_FILE.name} 必须是题目 ID 字符串数组")
    if len(payload) != len(set(payload)):
        raise ValueError(f"{PROGRAMMING_REMOVAL_FILE.name} 存在重复 ID")
    index = {str(question.get("id")): question for question in questions}
    removed = [index[qid] for qid in payload if qid in index]
    invalid = [q["id"] for q in removed if q.get("subject") != "编程语言"]
    if invalid:
        raise ValueError("范围校准只能移除编程语言题：" + "、".join(invalid[:20]))
    return set(payload)


def dedupe_base(questions: list[dict]):
    kept = []
    exact = {}
    removed = []
    for question in questions:
        key = (str(question.get("subject") or ""), compact_text(question.get("stem")))
        if key[1] and key in exact:
            removed.append((question, exact[key]))
            continue
        exact[key] = question
        kept.append(question)
    return kept, removed


def merge(base: list[dict], candidates: list[dict]):
    kept, removed_base = dedupe_base(base)
    exact_index = {
        (str(q.get("subject") or ""), compact_text(q.get("stem"))): q for q in kept
    }
    by_subject = defaultdict(list)
    for question in kept:
        by_subject[question.get("subject")].append(question)

    accepted = []
    skipped_exact = []
    skipped_fuzzy = []
    for candidate in candidates:
        key = (candidate["subject"], compact_text(candidate["stem"]))
        if key in exact_index:
            skipped_exact.append((candidate, exact_index[key]))
            continue
        matched = None
        matched_scores = None
        for existing in by_subject[candidate["subject"]]:
            duplicate, scores = is_near_duplicate(candidate, existing)
            if duplicate:
                matched, matched_scores = existing, scores
                break
        if matched:
            skipped_fuzzy.append((candidate, matched, matched_scores))
            continue
        accepted.append(candidate)
        kept.append(candidate)
        exact_index[key] = candidate
        by_subject[candidate["subject"]].append(candidate)
    return kept, accepted, removed_base, skipped_exact, skipped_fuzzy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只校验暂存题和当前合并结果")
    parser.add_argument("--question-js", type=Path, help="可选的浏览器题库生成物")
    args = parser.parse_args()

    all_current = json.loads(QUESTION_JSON.read_text(encoding="utf-8"))
    removal_ids = load_programming_removals(all_current)
    base = [
        q for q in all_current
        if not str(q.get("id") or "").startswith(MANAGED_PREFIXES)
        and str(q.get("id") or "") not in removal_ids
    ]
    candidates = apply_reviews(load_staging())
    merged, accepted, removed_base, skipped_exact, skipped_fuzzy = merge(base, candidates)
    hunan_recall = [q for q in merged if str(q.get("id") or "").startswith("hn-recall-")]
    merged = [q for q in merged if not str(q.get("id") or "").startswith("hn-recall-")] + hunan_recall
    derived_by_id = {
        str(question.get("id") or ""): {key: question[key] for key in DERIVED_METADATA_FIELDS if key in question}
        for question in all_current
    }
    merged = apply_reviews([{**question, **derived_by_id.get(str(question.get("id") or ""), {})} for question in merged])
    if args.check:
        if all_current != merged:
            raise SystemExit("questions.json 与去重合并结果不同步")
        if args.question_js is not None:
            if not args.question_js.is_file():
                raise SystemExit(f"缺少浏览器题库生成物：{args.question_js}")
            if not args.question_js.read_text(encoding="utf-8").strip() == (
                "window.QUESTIONS=" + json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + ";"
            ):
                raise SystemExit(f"{args.question_js.name} 与去重合并结果不同步")
        print(f"去重合并结果已同步：候选{len(candidates)}，入库{len(accepted)}，总题量{len(merged)}")
        return

    QUESTION_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    if args.question_js is not None:
        args.question_js.parent.mkdir(parents=True, exist_ok=True)
        args.question_js.write_text(
            "window.QUESTIONS=" + json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + ";\n",
            encoding="utf-8", newline="\n",
        )
    print(
        f"候选{len(candidates)}题，入库{len(accepted)}题，跳过精确{len(skipped_exact)}题、"
        f"高相似{len(skipped_fuzzy)}题；主库{len(base)}→{len(merged)}题。"
    )


if __name__ == "__main__":
    main()
