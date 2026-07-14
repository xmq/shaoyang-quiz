"""Validate lecture entry structure and chapter-level exam guidance."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COURSE_INDEX = ROOT / "course-index.json"
EXPECTED_COURSE_COUNT = 15

H1_RE = re.compile(r"^#[ \t]+(.+?)\s*$")
H2_RE = re.compile(r"^##[ \t]+(.+?)\s*$")
MARKER_RE = re.compile(r"^<!--\s*exam:\s*([ABC])\s*\|\s*(.+?)\s*-->$")
NON_KNOWLEDGE_RE = re.compile(r"(?:高频判断纠错|考前检查|考前自测)$")
BANNED_SECTION_RE = re.compile(r"基础简答题(?:答法|答题框架)")
ALLOWED_QUESTION_TYPES = frozenset({
    "单选",
    "多选",
    "判断",
    "填空",
    "计算",
    "程序阅读",
    "状态判断",
    "场景题",
    "排障题",
    "简答",
})


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def next_nonempty(lines: list[str], start: int) -> tuple[int, str] | None:
    for position in range(start, len(lines)):
        value = lines[position].strip()
        if value:
            return position, value
    return None


def main() -> int:
    configure_console()
    errors: list[str] = []
    levels: Counter[str] = Counter()
    marked_chapters = 0

    try:
        entries = json.loads(COURSE_INDEX.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法读取 {COURSE_INDEX.name}：{exc}", file=sys.stderr)
        return 1

    if not isinstance(entries, list) or len(entries) != EXPECTED_COURSE_COUNT:
        actual = len(entries) if isinstance(entries, list) else "非数组"
        errors.append(f"讲义索引应包含 {EXPECTED_COURSE_COUNT} 门课程，实际为 {actual}")
        entries = entries if isinstance(entries, list) else []

    for entry in entries:
        name = str(entry.get("name", "")).strip() if isinstance(entry, dict) else ""
        relative = str(entry.get("file", "")).strip() if isinstance(entry, dict) else ""
        path = ROOT / relative
        if not name or not relative or not path.is_file():
            errors.append(f"讲义索引项无效：{entry!r}")
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}：无法读取讲义：{exc}")
            continue

        first = next_nonempty(lines, 0)
        if first is None or not H1_RE.match(first[1]):
            errors.append(f"{name}：第一行有效内容必须是一级标题")
            continue
        first_body = next_nonempty(lines, first[0] + 1)
        if first_body is None or not H2_RE.match(first_body[1]):
            errors.append(f"{name}：课程标题后应直接进入第一个知识章节")

        knowledge_chapters = 0
        for position, line in enumerate(lines):
            h2 = H2_RE.match(line.strip())
            if not h2:
                continue
            title = h2.group(1).strip()
            if BANNED_SECTION_RE.search(title):
                errors.append(f"{name} / {title}：禁止使用通用简答题模板章节")
                continue
            if NON_KNOWLEDGE_RE.search(title):
                continue

            knowledge_chapters += 1
            following = next_nonempty(lines, position + 1)
            marker = MARKER_RE.match(following[1]) if following else None
            if not marker:
                errors.append(f"{name} / {title}：标题后缺少 exam 重要度与题型标记")
                continue

            question_types = [item.strip() for item in re.split(r"[、，,]", marker.group(2))]
            if any(not item for item in question_types):
                errors.append(f"{name} / {title}：题型标记中存在空项")
                continue
            unsupported = sorted(set(question_types) - ALLOWED_QUESTION_TYPES)
            if unsupported:
                errors.append(
                    f"{name} / {title}：存在未约定题型：{', '.join(unsupported)}"
                )
                continue
            if len(question_types) != len(set(question_types)):
                errors.append(f"{name} / {title}：题型标记存在重复项")
                continue
            levels[marker.group(1)] += 1
            marked_chapters += 1

        if knowledge_chapters == 0:
            errors.append(f"{name}：没有可学习的知识章节")

    if errors:
        print(f"讲义校验失败：共 {len(errors)} 个错误", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    level_text = "，".join(f"{level} 级 {levels[level]} 章" for level in "ABC")
    print(
        f"讲义校验通过：{len(entries)} 门课程，{marked_chapters} 个知识章节；{level_text}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
