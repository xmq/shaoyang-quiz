"""Validate that every course follows its maintained textbook chapter plan."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    plan = json.loads((ROOT / "textbook-map.json").read_text(encoding="utf-8"))
    guide = json.loads((ROOT / "course-guide.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    courses = plan.get("courses") if isinstance(plan, dict) else None
    if not isinstance(courses, list) or len(courses) != 16:
        errors.append("教材结构表必须包含16门课程")
        courses = courses if isinstance(courses, list) else []

    guide_courses = {item["name"]: item for item in guide.get("courses", [])}
    guide_refs = {item["id"]: item for item in guide.get("references", [])}
    chapter_total = 0
    for course in courses:
        name = str(course.get("name", "")).strip()
        textbooks = course.get("textbooks")
        chapters = course.get("chapters")
        url = str(course.get("url", ""))
        if not name or not isinstance(textbooks, list) or not textbooks:
            errors.append(f"{name or '未知课程'}：缺少主教材")
        if not url.startswith("https://"):
            errors.append(f"{name or '未知课程'}：教材链接无效")
        if not isinstance(chapters, list) or len(chapters) < 6 or len(chapters) != len(set(chapters)):
            errors.append(f"{name or '未知课程'}：教材章节为空、过少或重复")
            continue
        chapter_total += len(chapters)
        for index, title in enumerate(chapters, 1):
            if not re.match(rf"^第{index}章\s+\S", str(title)):
                errors.append(f"{name}：第{index}个章节编号或标题无效：{title}")

        for folder in ("course_notes", "color_notes"):
            path = ROOT / folder / f"{name}.md"
            if not path.is_file():
                errors.append(f"{name}：缺少{folder}文件")
                continue
            source = path.read_text(encoding="utf-8")
            actual = re.findall(r"(?m)^## (.+)$", source)
            if actual != chapters:
                errors.append(f"{name}：{folder}章节与教材结构表不一致")
        guide_course = guide_courses.get(name)
        if not guide_course:
            errors.append(f"{name}：课程范围表缺失")
            continue
        textbook_refs = [ref for ref in guide_course.get("references", []) if ref.startswith("textbook-")]
        if not textbook_refs or any(ref not in guide_refs for ref in textbook_refs):
            errors.append(f"{name}：课程范围表缺少有效教材记录")

    if errors:
        print(f"教材结构校验失败：{len(errors)}项", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"教材结构校验通过：{len(courses)}门课程，{chapter_total}章，讲义与重点页顺序一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
