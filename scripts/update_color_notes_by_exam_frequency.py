#!/usr/bin/env python3
"""Update three-color notes by weighted exam-frequency signals.

Rules:
1) Build knowledge-point frequency from questions.json with source weights.
2) Map question subjects to existing 15 courses (with keyword fallback for "计算机基础").
3) Reorder each card's three colored lines:
   - position 1: high-frequency item
   - position 2: medium-frequency item
   - position 3: low-frequency item
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "questions.json"
COLOR_INDEX_PATH = ROOT / "color-notes-index.json"

# Current note style uses these markers: red / blue / black circles.
RED = "\U0001F534"
BLUE = "\U0001F535"
BLACK = "\u26AB"

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s*$")
CARD_RE = re.compile(r"^###\s+(.+?)\s*$")
COLOR_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+)?(?P<color>["
                          + RED + BLUE + BLACK + r"])\s+(?P<text>.+?)\s*$")
PROMPT_RE = re.compile(r"^\s*(?:[-*+]\s+)?\s*(?:\*\*)?(?:提示|Note):\s*.*$", re.I)

SOURCE_WEIGHT = {
    "超格": 3.0,
    "德阳": 2.8,
    "中公": 2.8,
    "高校试题提炼": 2.1,
    "网络": 1.3,
    "新增": 1.2,
    "大数据基础题": 1.1,
    "大学期末改编": 1.0,
    "大学期末原创": 1.0,
}

COURSE_BY_SUBJECT = {
    "办公软件": "Office软件操作",
    "信息技术与教学论": "信息技术与教学论",
    "信息基础": "信息技术与教学论",
    "教学论": "信息技术与教学论",
    "多媒体": "多媒体技术",
    "操作系统": "操作系统原理",
    "数据库": "数据库技术",
    "算法与数据结构": "数据结构与算法",
    "编程语言": "编程语言",
    "计算机组成原理": "计算机组成原理",
    "计算机网络": "计算机网络",
    "电路分析与电工技术": "电路分析与电工技术",
    "模拟电子技术": "模拟电子技术",
    "数字电子技术": "数字电子技术",
    "通信原理与高频电子线路": "通信原理与高频电子线路",
    "软件工程": "软件工程",
    "信息安全": "信息安全",
    "大数据": "数据库技术",
}

COMPOSITE_RULES = {
    "计算机组成原理": (
        "cpu", "指令", "存储", "控制", "寄存器", "总线", "运算", "机器语言",
        "数制", "编码", "运算器", "硬件", "体系结构", "缓存",
    ),
    "计算机网络": (
        "网络", "tcp", "udp", "dns", "ipv", "子网", "路由", "交换", "osi",
        "传输层", "应用层", "网络层", "物理层", "局域网", "路由器", "交换机",
    ),
    "数据库技术": (
        "数据库", "sql", "关系模型", "事务", "并发", "索引", "范式", "模式",
        "er", "E-R", "hbase", "hdfs", "mapreduce", "spark", "hadoop", "redis",
    ),
    "编程语言": (
        "变量", "函数", "循环", "python", "c语言", "c++", "指针", "数组",
        "字符串", "运算符", "表达式", "异常", "结构体", "文件",
    ),
    "数据结构与算法": (
        "栈", "队列", "树", "图", "链表", "排序", "查找", "递归",
        "哈希", "散列表", "复杂度", "算法",
    ),
    "操作系统原理": (
        "进程", "线程", "调度", "内存", "文件系统", "死锁", "中断", "锁", "同步",
    ),
}


def normalize(text: object) -> str:
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = value.lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^\w]", "", value)
    return value


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_color_index() -> list[dict[str, object]]:
    raw = read_json(COLOR_INDEX_PATH)
    items: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        rel = str(item.get("file", "")).strip().replace("\\", "/")
        if not name or not rel:
            continue
        path = (ROOT / rel).resolve()
        items.append({"name": name, "relative": rel, "file": path})
    return items


def split_chapters(text: str) -> list[str]:
    return [match.group(1).strip() for match in CHAPTER_RE.finditer(text)]


def source_score(source_name: object) -> float:
    source = normalize(source_name)
    if not source:
        return 1.0
    for name, weight in SOURCE_WEIGHT.items():
        if normalize(name) in source:
            return weight
    return 1.0


def resolve_course(q: dict[str, object]) -> str | None:
    subject = str(q.get("subject", "")).strip()
    if subject in COURSE_BY_SUBJECT:
        return COURSE_BY_SUBJECT[subject]

    # Special handling for 计算机基础 (mixed content)
    if subject == "计算机基础":
        clue = normalize(f"{q.get('chapter','')} {q.get('source_chapter','')} "
                         f"{q.get('knowledge_point','')} {q.get('stem','')}")
        for course, keys in COMPOSITE_RULES.items():
            for key in keys:
                if normalize(key) in clue:
                    return course
        return "计算机组成原理"

    return None


def best_chapter_match(chapters: list[str], raw_chapter: str) -> str | None:
    if not raw_chapter:
        return None
    text = normalize(raw_chapter)
    if not text:
        return None
    best_name = None
    best_score = 0.0
    for name in chapters:
        norm_name = normalize(name)
        if not norm_name:
            continue
        if norm_name in text or text in norm_name:
            return name
        score = difflib.SequenceMatcher(None, text, norm_name).ratio()
        if score > best_score:
            best_score = score
            best_name = name
    return best_name if best_score >= 0.24 else None


def build_score_tables():
    questions = read_json(QUESTIONS_PATH)
    color_items = load_color_index()

    # course -> kp -> score
    global_scores: dict[str, dict[str, float]] = defaultdict(Counter)
    # course -> chapter -> kp -> score
    chapter_scores: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(Counter)
    )

    chapter_cache: dict[str, list[str]] = {}
    for item in color_items:
        chapter_cache[item["name"]] = split_chapters(Path(item["file"]).read_text(encoding="utf-8"))

    unknown_subjects = Counter()

    for q in questions:
        if not isinstance(q, dict):
            continue
        course = resolve_course(q)
        if not course or course not in chapter_cache:
            unknown_subjects[q.get("subject", "")] += 1
            continue

        kp = str(q.get("knowledge_point", "")).strip()
        if not kp:
            continue

        score = source_score(q.get("source", ""))
        global_scores[course][kp] += score

        chapter_raw = str(q.get("chapter", "") or q.get("source_chapter", "") or "")
        mapped_chapter = best_chapter_match(chapter_cache[course], chapter_raw)
        if mapped_chapter:
            chapter_scores[course][mapped_chapter][kp] += score

    return global_scores, chapter_scores, unknown_subjects


def choose_level(score_map: dict[str, float], kp_name: str) -> str:
    if not score_map:
        return "black"

    ranked = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)
    rank = next((idx for idx, (name, _) in enumerate(ranked, start=1) if name == kp_name), None)
    if rank is None:
        return "black"

    total = len(ranked)
    red_count = max(1, round(total * 0.2))
    yellow_count = max(red_count + 1, round(total * 0.5))

    if rank <= red_count:
        return "red"
    if rank <= yellow_count:
        return "yellow"
    return "black"


def choose_kp(score_map: dict[str, float], card_title: str, body_text: str) -> tuple[str, float]:
    if not score_map:
        return "", 0.0

    text = normalize(f"{card_title} {body_text}")
    ordered = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)

    for kp, score in ordered:
        if normalize(kp) in text:
            return kp, float(score)

    # fuzzy fallback
    best_kp, best_score = ordered[0]
    best_ratio = 0.0
    for kp, score in ordered:
        ratio = difflib.SequenceMatcher(None, text, normalize(kp)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_kp = kp
            best_score = score
    return best_kp, float(best_score)


def reorder_colors(card_body: list[str], level: str, kp_name: str, kp_score: float) -> list[str]:
    prompt_lines: list[str] = []
    color_lines: list[str] = []
    extra_lines: list[str] = []

    for line in card_body:
        if PROMPT_RE.match(line.strip()):
            prompt_lines.append(line)
            continue
        m = COLOR_LINE_RE.match(line)
        if m:
            color_lines.append(m.group("text").strip())
            continue
        extra_lines.append(line)

    while len(color_lines) < 3:
        color_lines.append("待补充")
    color_lines = color_lines[:3]

    if level == "red":
        order = (RED, BLUE, BLACK)
    elif level == "yellow":
        order = (BLUE, RED, BLACK)
    else:
        order = (BLACK, BLUE, RED)

    # Keep useful provenance in first line for review only; not used in renderer.
    # Keep line in plain text to reduce visual noise for users.
    return (
        [*prompt_lines, *extra_lines]
        + [f"- {order[0]} {color_lines[0]}",
           f"- {order[1]} {color_lines[1]}",
           f"- {order[2]} {color_lines[2]}"]
    )


def update_course_note(item: dict[str, object], global_scores: dict[str, float], chapter_scores: dict[str, dict[str, float]]) -> None:
    path = Path(item["file"])
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chapters = split_chapters(text)

    current_chapter = ""
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        ch = CHAPTER_RE.match(line)
        if ch:
            current_chapter = ch.group(1).strip()
            output.append(line)
            i += 1
            continue

        card = CARD_RE.match(line)
        if not card:
            output.append(line)
            i += 1
            continue

        output.append(line)
        i += 1
        card_title = card.group(1).strip()
        card_body: list[str] = []
        while i < len(lines):
            next_line = lines[i]
            if CHAPTER_RE.match(next_line) or CARD_RE.match(next_line):
                break
            card_body.append(next_line)
            i += 1

        mapped_scores: dict[str, float] = {}
        if current_chapter and chapters and current_chapter in chapter_scores:
            mapped_scores = chapter_scores[current_chapter]
        score_map = mapped_scores if mapped_scores else global_scores

        if score_map:
            kp_name, kp_score = choose_kp(score_map, card_title, "\n".join(card_body))
            level = choose_level(score_map, kp_name)
            output.extend(reorder_colors(card_body, level, kp_name, kp_score))
        else:
            output.extend(reorder_colors(card_body, "black", "", 0.0))

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update three-color notes by exam frequency")
    parser.add_argument("--check", action="store_true", help="Dry run only, no writes")
    parser.add_argument("--verbose", action="store_true", help="Print mapping summary")
    args = parser.parse_args()

    global_scores, chapter_scores, unknown_subjects = build_score_tables()

    if args.verbose:
        print("Top knowledge points by course:")
        for course, values in sorted(global_scores.items()):
            print(f"- {course}")
            for kp, score in sorted(values.items(), key=lambda kv: kv[1], reverse=True)[:6]:
                print(f"  {kp}: {score:.1f}")
        if unknown_subjects:
            print("Unmapped subject records:", sum(unknown_subjects.values()))
            for subject, count in sorted(unknown_subjects.items(), key=lambda x: x[1], reverse=True):
                print(f"  {subject!r}: {count}")

    if args.check:
        return

    items = load_color_index()
    for item in items:
        update_course_note(item, global_scores.get(item["name"], {}), chapter_scores.get(item["name"], {}))


if __name__ == "__main__":
    main()
