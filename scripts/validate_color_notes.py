"""Validate the frequency-based three-color notes."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLOR_INDEX = ROOT / "color-notes-index.json"
LECTURE_INDEX = ROOT / "course-index.json"
EXPECTED_COURSE_COUNT = 15
MAX_LENGTH_RATIO = 0.85
MIN_ITEMS = {"🔴": 5, "🔵": 4, "⚫": 3}

H2_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
ITEM_RE = re.compile(r"(?m)^-\s+(🔴|🔵|⚫)\s+\*\*(.+?)\*\*：(.+)$")


@dataclass
class CourseStats:
    name: str
    red: int = 0
    blue: int = 0
    black: int = 0
    color_chars: int = 0
    lecture_chars: int = 0
    ratio: float = 0.0
    errors: int = 0


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def load_index(path: Path, expected_folder: str, errors: list[str]) -> list[dict[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"无法读取索引 {path.name}: {exc}")
        return []
    if not isinstance(raw, list):
        errors.append(f"{path.name} 必须是数组")
        return []

    items: list[dict[str, object]] = []
    seen_names: set[str] = set()
    seen_files: set[str] = set()
    for position, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            errors.append(f"{path.name} 第 {position} 项不是对象")
            continue
        name = str(item.get("name", "")).strip()
        relative = str(item.get("file", "")).strip().replace("\\", "/")
        if not name or not relative:
            errors.append(f"{path.name} 第 {position} 项缺少 name/file")
            continue
        if name in seen_names:
            errors.append(f"{path.name} 课程名重复: {name}")
        if relative in seen_files:
            errors.append(f"{path.name} 文件重复: {relative}")
        if not relative.startswith(f"{expected_folder}/"):
            errors.append(f"{path.name} 路径不在 {expected_folder}/: {relative}")

        file_path = (ROOT / relative).resolve()
        if ROOT != file_path and ROOT not in file_path.parents:
            errors.append(f"{path.name} 路径越出 web 目录: {relative}")
        elif not file_path.is_file():
            errors.append(f"{path.name} 所列文件不存在: {relative}")

        items.append({"name": name, "relative": relative, "path": file_path})
        seen_names.add(name)
        seen_files.add(relative)
    return items


def validate_index_coverage(
    color_items: list[dict[str, object]],
    lecture_items: list[dict[str, object]],
    errors: list[str],
) -> None:
    if len(color_items) != EXPECTED_COURSE_COUNT:
        errors.append(f"三色笔记索引应有 {EXPECTED_COURSE_COUNT} 门，实际 {len(color_items)} 门")
    if len(lecture_items) != EXPECTED_COURSE_COUNT:
        errors.append(f"讲义索引应有 {EXPECTED_COURSE_COUNT} 门，实际 {len(lecture_items)} 门")

    color_names = [str(item["name"]) for item in color_items]
    lecture_names = [str(item["name"]) for item in lecture_items]
    if set(color_names) != set(lecture_names):
        errors.append("三色笔记索引与讲义索引课程集合不一致")
    elif color_names != lecture_names:
        errors.append("三色笔记索引与讲义索引课程顺序不一致")


def read_text(path: Path, label: str, errors: list[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"无法读取 {label} {path}: {exc}")
        return ""
    if "\ufffd" in text:
        errors.append(f"{label} 含无效替换字符: {path}")
    return text


def validate_note(name: str, text: str, lecture_text: str, errors: list[str]) -> CourseStats:
    stats = CourseStats(name=name, color_chars=len(text), lecture_chars=len(lecture_text))
    stats.ratio = stats.color_chars / stats.lecture_chars if stats.lecture_chars else 0.0

    if "回忆卡" in text or "先答" in text or "点击核对" in text:
        errors.append(f"{name}: 仍残留回忆卡式文案")

    sections = H2_RE.findall(text)
    for required in ("🔴 高频考点", "🔵 中频考点", "⚫ 低频了解"):
        if required not in sections:
            errors.append(f"{name}: 缺少章节 {required}")

    counts = {"🔴": 0, "🔵": 0, "⚫": 0}
    topics: set[str] = set()
    for marker, title, body in ITEM_RE.findall(text):
        counts[marker] += 1
        normalized_title = re.sub(r"\s+", "", title)
        if normalized_title in topics:
            errors.append(f"{name}: 知识点重复 {title}")
        topics.add(normalized_title)
        if "常见考法：" not in body or "易错边界：" not in body:
            errors.append(f"{name}: {title} 缺少常见考法或易错边界")
        if len(body.strip()) < 35:
            errors.append(f"{name}: {title} 内容过短")

    stats.red = counts["🔴"]
    stats.blue = counts["🔵"]
    stats.black = counts["⚫"]
    for marker, minimum in MIN_ITEMS.items():
        if counts[marker] < minimum:
            errors.append(f"{name}: {marker} 条目不足，至少 {minimum} 条，实际 {counts[marker]} 条")

    if stats.lecture_chars and stats.ratio > MAX_LENGTH_RATIO:
        errors.append(f"{name}: 三色笔记长度为讲义的 {stats.ratio:.1%}，超过 {MAX_LENGTH_RATIO:.0%}")

    return stats


def print_report(stats: list[CourseStats]) -> None:
    print("课程 | 红 | 蓝 | 黑 | 三色字符 | 讲义字符 | 长度比 | 状态")
    print("-" * 78)
    for item in stats:
        status = "通过" if item.errors == 0 else f"错误 {item.errors}"
        print(
            f"{item.name} | {item.red} | {item.blue} | {item.black} | "
            f"{item.color_chars} | {item.lecture_chars} | {item.ratio:.1%} | {status}"
        )


def main() -> int:
    configure_console()
    global_errors: list[str] = []
    color_items = load_index(COLOR_INDEX, "color_notes", global_errors)
    lecture_items = load_index(LECTURE_INDEX, "course_notes", global_errors)
    validate_index_coverage(color_items, lecture_items, global_errors)

    lecture_by_name = {str(item["name"]): item for item in lecture_items}
    stats: list[CourseStats] = []
    all_errors = list(global_errors)
    for color_item in color_items:
        name = str(color_item["name"])
        course_errors: list[str] = []
        color_text = read_text(Path(color_item["path"]), "三色笔记", course_errors)
        lecture_item = lecture_by_name.get(name)
        lecture_text = ""
        if lecture_item is None:
            course_errors.append(f"{name}: 找不到对应讲义")
        else:
            lecture_text = read_text(Path(lecture_item["path"]), "讲义", course_errors)
        item_stats = validate_note(name, color_text, lecture_text, course_errors)
        item_stats.errors = len(course_errors)
        stats.append(item_stats)
        all_errors.extend(course_errors)

    print_report(stats)
    if all_errors:
        print(f"\n校验失败: 共 {len(all_errors)} 个错误", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"\n校验通过: {len(stats)} 门课程均符合三色笔记规范。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
