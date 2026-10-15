"""Build the separate lecture and three-color-note modules from Markdown."""

from pathlib import Path
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "notes.template.html"
LEGACY_MARKDOWN_OUTPUT = ROOT / "讲义三色笔记.md"

RED_STYLE = "color:#c62828;font-weight:700"
BLUE_STYLE = "color:#1565c0;font-weight:700"
CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百\d]+(?:章|节|篇|部分)[：:]?")
POINT_RE = re.compile(r"^(?:考点|专题|模块)\s*\d+[：:]?")

PAGE_CONFIGS = {
    "lecture": {
        "index": ROOT / "course-index.json",
        "html": ROOT / "notes.html",
        "markdown": ROOT / "零基础讲义完整版.md",
        "document_title": "知阶 · 课程讲义",
        "markdown_title": "知阶 · 课程讲义完整版",
        "active_module": "lecture",
        "use_color_markup": False,
        "body_class": "lecture-page",
    },
    "color-notes": {
        "index": ROOT / "color-notes-index.json",
        "html": ROOT / "color-notes.html",
        "markdown": ROOT / "三色笔记完整版.md",
        "document_title": "知阶 · 重点与易错",
        "markdown_title": "知阶 · 重点与易错完整版",
        "active_module": "color-notes",
        "use_color_markup": True,
        "body_class": "color-notes-page",
    },
}


def load_courses(index_path):
    if not index_path.is_file():
        raise ValueError(f"缺少课程索引：{index_path.name}")
    items = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError(f"{index_path.name} 必须是非空数组")

    seen_names = set()
    seen_files = set()
    courses = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"课程索引项必须是对象：{item!r}")
        name = str(item.get("name", "")).strip()
        rel = str(item.get("file", "")).strip()
        if not name or not rel or name in seen_names or rel in seen_files:
            raise ValueError(f"课程索引无效或重复：{item!r}")
        path = (ROOT / rel).resolve()
        if ROOT not in path.parents or not path.is_file():
            raise ValueError(f"课程文件不存在或超出 web 目录：{rel}")
        text = path.read_text(encoding="utf-8").strip() + "\n"
        if "\ufffd" in text:
            raise ValueError(f"课程文件含无效替换字符：{rel}")
        courses.append({"name": name, "file": rel, "text": text})
        seen_names.add(name)
        seen_files.add(rel)
    return courses


def render_html(courses, config):
    if not TEMPLATE.exists():
        raise ValueError("缺少 notes.template.html，无法构建学习页面")
    rendered = TEMPLATE.read_text(encoding="utf-8")
    learning_map = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    question_counts = {}
    for question in questions:
        topic_id = question.get("topic_id")
        if topic_id:
            question_counts[topic_id] = question_counts.get(topic_id, 0) + 1
    topics_by_course = {
        course["course_name"]: [
            {**topic, "question_count": question_counts.get(topic["topic_id"], 0)}
            for topic in course.get("topics", [])
        ]
        for course in learning_map["courses"]
    }
    lecture_courses = load_courses(ROOT / "course-index.json")
    note_courses = load_courses(ROOT / "color-notes-index.json")
    chapters = {
        kind: {item["name"]: re.findall(r"(?m)^## (.+)$", item["text"]) for item in items}
        for kind, items in (("lecture", lecture_courses), ("color-notes", note_courses))
    }
    payload_items = []
    for item in courses:
        learning_course = next(course for course in learning_map["courses"] if course["course_name"] == item["name"])
        payload_items.append({
            "name": item["name"], "text": item["text"],
            "chapters": {kind: values[item["name"]] for kind, values in chapters.items()},
            "learning_chapters": next(
                (course.get("chapters", []) for course in learning_map["courses"] if course["course_name"] == item["name"]),
                [],
            ),
            "topics": topics_by_course.get(item["name"], []),
            "chapter_ids": [chapter["chapter_id"] for chapter in learning_course["chapters"]],
            "review_topic_ids": [
                [topic["topic_id"] for topic in learning_course["topics"] if topic["chapter_id"] == chapter["chapter_id"]]
                for chapter in learning_course["chapters"]
            ],
            **{key: learning_course[key] for key in ("layout_revision", "previous_layout", "keep_completed") if key in learning_course},
        })
    payload = json.dumps(payload_items, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    image_sizes = {}
    for path in (ROOT / "media").rglob("*.svg"):
        box = ET.parse(path).getroot().get("viewBox", "").replace(",", " ").split()
        if len(box) == 4 and float(box[2]) > 0 and float(box[3]) > 0:
            image_sizes[path.relative_to(ROOT).as_posix()] = [float(box[2]), float(box[3])]
    replacements = {
        "__IMAGE_SIZES__": json.dumps(image_sizes, sort_keys=True, separators=(",", ":")),
        "__COURSE_DATA__": payload,
        "__DOCUMENT_TITLE__": config["document_title"],
        "__COLOR_MODE__": "true" if config["use_color_markup"] else "false",
        "__PAGE_KIND__": config["active_module"],
        "__PAGE_BODY_CLASS__": config["body_class"],
        "__LECTURE_CURRENT__": 'aria-current="page"' if config["active_module"] == "lecture" else "",
        "__COLOR_NOTES_CURRENT__": 'aria-current="page"' if config["active_module"] == "color-notes" else "",
    }
    for placeholder, value in replacements.items():
        if rendered.count(placeholder) != 1:
            raise ValueError(f"notes.template.html 必须且只能包含一个占位符：{placeholder}")
        rendered = rendered.replace(placeholder, value)
    leftovers = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", rendered)))
    if leftovers:
        raise ValueError(f"notes.template.html 含未替换占位符：{', '.join(leftovers)}")
    return rendered


def color_line(line):
    if line.startswith("🔴"):
        return f'<span style="{RED_STYLE}">{line}</span>'
    if line.startswith("🔵"):
        return f'<span style="{BLUE_STYLE}">{line}</span>'
    return line


def render_course_markdown(course, use_color_markup):
    lines = course["text"].splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]

    rendered = [f'## {course["name"]}', ""]
    first_content = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if rendered[-1] != "":
                rendered.append("")
            continue
        if first_content and stripped.startswith("使用说明"):
            continue
        if stripped.startswith("## "):
            rendered.extend([f"### {stripped[3:].strip()}", ""])
            first_content = False
            continue
        if stripped.startswith("### "):
            rendered.extend([f"#### {stripped[4:].strip()}", ""])
            first_content = False
            continue
        if CHAPTER_RE.match(stripped):
            rendered.extend([f"### {stripped}", ""])
            first_content = False
            continue
        if POINT_RE.match(stripped):
            rendered.extend([f"#### {stripped}", ""])
            first_content = False
            continue

        if stripped.startswith("![") and "](../media/" in stripped:
            stripped = stripped.replace("](../media/", "](media/")
        converted = color_line(stripped) if use_color_markup else stripped
        if first_content:
            converted = f"> {converted}"
            first_content = False
        rendered.append(converted)

    while rendered and not rendered[-1]:
        rendered.pop()
    return "\n".join(rendered)


def render_markdown(courses, config):
    header = f'# {config["markdown_title"]}\n\n---\n\n'
    body = "\n\n---\n\n".join(
        render_course_markdown(course, config["use_color_markup"]) for course in courses
    )
    return header + body + "\n"


def render_legacy_pointer():
    return (
        "# 讲义与三色笔记已拆分\n\n"
        "为避免把系统学习、考前记忆和刷题混在一起，请改用以下独立模块：\n\n"
        "- [零基础讲义完整版](零基础讲义完整版.md)\n"
        "- [三色笔记完整版](三色笔记完整版.md)\n"
        "- [习题训练网页版](quiz.html)\n"
    )


def check_output(path, expected):
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != expected:
        print(f"{path.name} 与源 Markdown 不同步", file=sys.stderr)
        return False
    return True


def select_configs(target):
    return PAGE_CONFIGS.items() if target == "all" else [(target, PAGE_CONFIGS[target])]


def main():
    parser = argparse.ArgumentParser(description="分别构建零基础讲义和三色笔记页面")
    parser.add_argument("--check", action="store_true", help="只检查生成物是否同步")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="生成物目录（默认：dist）",
    )
    parser.add_argument(
        "--include-markdown",
        action="store_true",
        help="同时生成合并版 Markdown（默认只生成网页）",
    )
    parser.add_argument(
        "--target",
        choices=("all", *PAGE_CONFIGS),
        default="all",
        help="构建全部模块或指定模块（默认：all）",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()

    rendered_pages = []
    for key, config in select_configs(args.target):
        courses = load_courses(config["index"])
        rendered_pages.append((key, config, courses, render_html(courses, config), render_markdown(courses, config)))

    legacy_pointer = render_legacy_pointer()
    if args.check:
        ok = True
        for _, config, _, html, markdown in rendered_pages:
            ok &= check_output(output_dir / config["html"].name, html)
            if args.include_markdown:
                ok &= check_output(output_dir / config["markdown"].name, markdown)
        if args.target == "all" and args.include_markdown:
            ok &= check_output(output_dir / LEGACY_MARKDOWN_OUTPUT.name, legacy_pointer)
        if not ok:
            raise SystemExit(1)
        counts = "、".join(
            f"{config['document_title']} {len(courses)} 门"
            for _, config, courses, _, _ in rendered_pages
        )
        print(f"生成物已同步：{counts}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    for _, config, courses, html, markdown in rendered_pages:
        (output_dir / config["html"].name).write_text(html, encoding="utf-8", newline="\n")
        if args.include_markdown:
            (output_dir / config["markdown"].name).write_text(markdown, encoding="utf-8", newline="\n")
        suffix = f" 和 {config['markdown'].name}" if args.include_markdown else ""
        print(f"已生成 {config['html'].name}{suffix}：{len(courses)} 门课程")
    if args.target == "all" and args.include_markdown:
        (output_dir / LEGACY_MARKDOWN_OUTPUT.name).write_text(legacy_pointer, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
