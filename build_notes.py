from pathlib import Path
import argparse
import json
import re
import sys


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "course-index.json"
TEMPLATE = ROOT / "notes.template.html"
HTML_OUTPUT = ROOT / "notes.html"
MARKDOWN_OUTPUT = ROOT / "讲义三色笔记.md"

RED_STYLE = "color:#c62828;font-weight:700"
BLUE_STYLE = "color:#1565c0;font-weight:700"
CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百\d]+(?:章|节|篇|部分)[：:]?")
POINT_RE = re.compile(r"^(?:考点|专题|模块)\s*\d+[：:]?")


def load_courses():
    items = json.loads(INDEX.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError("course-index.json 必须是非空数组")

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


def render_html(courses):
    if not TEMPLATE.exists():
        raise ValueError("缺少 notes.template.html，无法构建讲义页面")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__COURSE_DATA__") != 1:
        raise ValueError("notes.template.html 必须且只能包含一个课程数据占位符")
    payload_items = [{"name": item["name"], "text": item["text"]} for item in courses]
    payload = json.dumps(payload_items, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("__COURSE_DATA__", payload)


def color_line(line):
    if line.startswith("🔴"):
        return f'<span style="{RED_STYLE}">{line}</span>'
    if line.startswith("🔵"):
        return f'<span style="{BLUE_STYLE}">{line}</span>'
    return line


def render_course_markdown(course):
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

        converted = color_line(stripped)
        if first_content:
            converted = f"> {converted}"
            first_content = False
        rendered.append(converted)

    while rendered and not rendered[-1]:
        rendered.pop()
    return "\n".join(rendered)


def render_markdown(courses):
    header = (
        "# 计算机岗位考试 · 三色笔记完整版\n\n"
        "---\n\n"
    )
    body = "\n\n---\n\n".join(render_course_markdown(course) for course in courses)
    return header + body + "\n"


def check_output(path, expected):
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != expected:
        print(f"{path.name} 与课程 Markdown 不同步", file=sys.stderr)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="从 course_notes 单一数据源构建讲义页面和总笔记")
    parser.add_argument("--check", action="store_true", help="只检查生成物是否同步")
    args = parser.parse_args()

    courses = load_courses()
    html = render_html(courses)
    markdown = render_markdown(courses)
    if args.check:
        ok = check_output(HTML_OUTPUT, html) & check_output(MARKDOWN_OUTPUT, markdown)
        if not ok:
            raise SystemExit(1)
        print(f"讲义生成物已与 {len(courses)} 门课程 Markdown 同步")
        return

    HTML_OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    MARKDOWN_OUTPUT.write_text(markdown, encoding="utf-8", newline="\n")
    print(f"已生成 {HTML_OUTPUT.name} 和 {MARKDOWN_OUTPUT.name}：{len(courses)} 门课程")


if __name__ == "__main__":
    main()
