"""Validate the structure and size of the 15 three-color recall-note courses."""

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
MAX_LENGTH_RATIO = 0.65
MIN_CARDS_PER_CHAPTER = 1
MAX_CARDS_PER_CHAPTER = 7
MAX_UNCOLORED_LINE_CHARS = 44
MAX_UNCOLORED_TOTAL_CHARS = 70

H2_RE = re.compile(r"(?m)^##[ \t]+(.+?)[ \t]*$")
H3_RE = re.compile(r"(?m)^###[ \t]+(.+?)[ \t]*$")
PROMPT_LINE_RE = re.compile(
    r"^\s*(?:(?:[-*+]\s+)|(?:\d+[.)]\s+))?(?:>\s*)?(?:\*\*)?先答：.+?(?:\*\*)?\s*$"
)
COLOR_LINE_RES = {
    color: re.compile(
        rf"^\s*(?:(?:[-*+]\s+)|(?:\d+[.)]\s+))?(?:>\s*)?(?:\*\*)?{re.escape(color)}"
    )
    for color in ("🔴", "🔵", "⚫")
}
SAFE_META_RE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:"
    r"自评|掌握状态|回讲义|去刷题|练同考点|不会时|犹豫时|"
    r"\[(?:会|犹豫|不会|回讲义|去刷题|练同考点)[^]]*\]"
    r")"
)


@dataclass
class CourseStats:
    name: str
    chapters: int = 0
    cards: int = 0
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


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_index(path: Path, expected_folder: str, errors: list[str]) -> list[dict[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"缺少索引：{path.name}")
        return []
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"无法读取索引 {path.name}：{exc}")
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
            errors.append(f"{path.name} 课程名重复：{name}")
            continue
        if relative in seen_files:
            errors.append(f"{path.name} 文件重复：{relative}")
            continue

        file_path = (ROOT / relative).resolve()
        if not relative.startswith(f"{expected_folder}/"):
            errors.append(f"{path.name} 路径不在 {expected_folder}/：{relative}")
        if ROOT != file_path and ROOT not in file_path.parents:
            errors.append(f"{path.name} 路径越出 web 目录：{relative}")
        elif not file_path.is_file():
            errors.append(f"{path.name} 所列文件不存在：{relative}")

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
        errors.append(
            f"三色笔记索引应有 {EXPECTED_COURSE_COUNT} 门，实际 {len(color_items)} 门"
        )
    if len(lecture_items) != EXPECTED_COURSE_COUNT:
        errors.append(
            f"讲义索引应有 {EXPECTED_COURSE_COUNT} 门，实际 {len(lecture_items)} 门"
        )

    color_names = [str(item["name"]) for item in color_items]
    lecture_names = [str(item["name"]) for item in lecture_items]
    missing_color = sorted(set(lecture_names) - set(color_names))
    missing_lecture = sorted(set(color_names) - set(lecture_names))
    if missing_color:
        errors.append(f"三色笔记索引缺课：{', '.join(missing_color)}")
    if missing_lecture:
        errors.append(f"讲义索引缺少对应课程：{', '.join(missing_lecture)}")
    if not missing_color and not missing_lecture and color_names != lecture_names:
        errors.append("三色笔记索引与讲义索引的课程顺序不一致")

    indexed_color_files = {str(item["relative"]) for item in color_items}
    actual_color_files = {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "color_notes").glob("*.md")
    }
    unindexed = sorted(actual_color_files - indexed_color_files)
    missing_files = sorted(indexed_color_files - actual_color_files)
    if unindexed:
        errors.append(f"color_notes 中存在未入索引文件：{', '.join(unindexed)}")
    if missing_files:
        errors.append(f"索引所列三色笔记缺失：{', '.join(missing_files)}")


def visible_length(line: str) -> int:
    text = re.sub(r"https?://\S+", "", line)
    text = re.sub(r"[`*_>#|\[\]()-]", "", text)
    text = re.sub(r"\s+", "", text)
    return len(text)


def validate_card(
    course: str,
    chapter: str,
    title: str,
    body: str,
    errors: list[str],
) -> None:
    label = f"{course} / {chapter} / {title}"
    prompt_occurrences = body.count("先答：")
    prompt_lines = [line for line in body.splitlines() if PROMPT_LINE_RE.match(line)]
    if prompt_occurrences != 1 or len(prompt_lines) != 1:
        errors.append(
            f"{label}：必须恰好有 1 行“先答：”提示，实际出现 {prompt_occurrences} 次"
        )

    for color, line_re in COLOR_LINE_RES.items():
        count = sum(1 for line in body.splitlines() if line_re.match(line))
        if count < 1:
            errors.append(f"{label}：缺少以 {color} 开头的答案条目")

    if "```" in body or "~~~" in body:
        errors.append(f"{label}：卡片内禁止代码块，避免回忆模式提前泄露答案")

    uncolored_total = 0
    for line_number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or PROMPT_LINE_RE.match(line):
            continue
        if any(line_re.match(line) for line_re in COLOR_LINE_RES.values()):
            continue
        if stripped.startswith("<!--") or SAFE_META_RE.match(line):
            continue
        length = visible_length(line)
        if length == 0:
            continue
        uncolored_total += length
        if length > MAX_UNCOLORED_LINE_CHARS:
            errors.append(
                f"{label}：卡片正文第 {line_number} 行有 {length} 个未着色字符，疑似答案泄露"
            )
    if uncolored_total > MAX_UNCOLORED_TOTAL_CHARS:
        errors.append(
            f"{label}：卡片累计有 {uncolored_total} 个未着色正文字符，疑似拆行答案泄露"
        )


def validate_note_structure(name: str, text: str, errors: list[str]) -> tuple[int, int]:
    chapter_matches = list(H2_RE.finditer(text))
    if not chapter_matches:
        errors.append(f"{name}：没有二级章节（##）")
        return 0, 0

    total_cards = 0
    for chapter_index, chapter_match in enumerate(chapter_matches):
        chapter_title = chapter_match.group(1).strip()
        chapter_end = (
            chapter_matches[chapter_index + 1].start()
            if chapter_index + 1 < len(chapter_matches)
            else len(text)
        )
        chapter_body = text[chapter_match.end() : chapter_end]
        h3_matches = list(H3_RE.finditer(chapter_body))
        card_matches = [match for match in h3_matches if match.group(1).strip().startswith("回忆卡")]
        card_count = len(card_matches)
        total_cards += card_count
        if not MIN_CARDS_PER_CHAPTER <= card_count <= MAX_CARDS_PER_CHAPTER:
            errors.append(
                f"{name} / {chapter_title}：回忆卡应为 "
                f"{MIN_CARDS_PER_CHAPTER}-{MAX_CARDS_PER_CHAPTER} 张，实际 {card_count} 张"
            )

        for match in card_matches:
            h3_position = h3_matches.index(match)
            card_end = (
                h3_matches[h3_position + 1].start()
                if h3_position + 1 < len(h3_matches)
                else len(chapter_body)
            )
            card_body = chapter_body[match.end() : card_end]
            validate_card(
                name,
                chapter_title,
                match.group(1).strip(),
                card_body,
                errors,
            )
    return len(chapter_matches), total_cards


def read_markdown(path: Path, label: str, errors: list[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"无法读取 {label} {display_path(path)}：{exc}")
        return ""
    if "\ufffd" in text:
        errors.append(f"{label} 含无效替换字符：{display_path(path)}")
    return text


def print_report(stats: list[CourseStats]) -> None:
    print("课程 | 章节 | 回忆卡 | 三色字符 | 讲义字符 | 长度比 | 状态")
    print("-" * 86)
    for item in stats:
        status = "通过" if item.errors == 0 else f"错误 {item.errors}"
        print(
            f"{item.name} | {item.chapters} | {item.cards} | "
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
        color_path = Path(color_item["path"])
        color_text = read_markdown(color_path, "三色笔记", course_errors)
        lecture_item = lecture_by_name.get(name)
        lecture_text = ""
        if lecture_item is None:
            course_errors.append(f"{name}：找不到对应讲义")
        else:
            lecture_text = read_markdown(Path(lecture_item["path"]), "讲义", course_errors)

        chapters, cards = validate_note_structure(name, color_text, course_errors)
        color_chars = len(color_text)
        lecture_chars = len(lecture_text)
        ratio = color_chars / lecture_chars if lecture_chars else 0.0
        if lecture_chars and ratio > MAX_LENGTH_RATIO:
            course_errors.append(
                f"{name}：三色笔记长度为讲义的 {ratio:.1%}，超过 {MAX_LENGTH_RATIO:.0%}"
            )

        stats.append(
            CourseStats(
                name=name,
                chapters=chapters,
                cards=cards,
                color_chars=color_chars,
                lecture_chars=lecture_chars,
                ratio=ratio,
                errors=len(course_errors),
            )
        )
        all_errors.extend(course_errors)

    print_report(stats)
    if all_errors:
        print(f"\n校验失败：共 {len(all_errors)} 个错误", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"\n校验通过：{len(stats)} 门课程全部符合三色回忆卡规范。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
