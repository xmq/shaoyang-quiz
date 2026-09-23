"""Validate chapter notes, lecture links and the scope of exam evidence."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate():
    errors = []
    notes = json.loads((ROOT / "color-notes-index.json").read_text(encoding="utf-8"))
    lectures = json.loads((ROOT / "course-index.json").read_text(encoding="utf-8"))
    guide = json.loads((ROOT / "course-guide.json").read_text(encoding="utf-8"))
    exams = json.loads((ROOT / "exam-sources.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in lectures]
    if "信息技术与教学论" in names or any(item["group"] == "信息技术教师方向" for item in guide["courses"]):
        errors.append("教师方向已移除，不应重新加入现行课程")
    if len(set(names)) != len(names) or set(names) != {item["name"] for item in notes}:
        errors.append("讲义与重点课程集合不同或存在重复")
    guide_names = [item["name"] for item in guide["courses"]]
    if set(names) != set(guide_names) or len(set(guide_names)) != len(guide_names):
        errors.append("课程范围表与讲义索引不一致或存在重复")
    lecture_map = {item["name"]: item for item in lectures}
    cards = 0
    chapters = 0
    for item in notes:
        path = (ROOT / item["file"]).resolve()
        if ROOT not in path.parents or not path.is_file():
            errors.append(f"重点路径无效：{item['file']}")
            continue
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            errors.append(f"{item['name']}：含无效替换字符")
        if "重点与易错" not in text.splitlines()[0]:
            errors.append(f"{item['name']}：标题未更新")
        if re.search(r"(?m)^##.*(?:高频考点|中频考点|低频了解)", text):
            errors.append(f"{item['name']}：仍按未经证实的考频分组")
        lecture = lecture_map.get(item["name"])
        if not lecture:
            continue
        lecture_text = (ROOT / lecture["file"]).read_text(encoding="utf-8")
        lecture_titles = re.findall(r"(?m)^## (.+)$", lecture_text)
        sections = re.split(r"(?m)^## (.+)\n", text)
        titles = sections[1::2]
        if not titles or len(set(titles)) != len(titles):
            errors.append(f"{item['name']}：章节为空或重复")
        for title, body in zip(sections[1::2], sections[2::2]):
            chapters += 1
            if title not in lecture_titles:
                errors.append(f"{item['name']}：章节没有对应讲义：{title}")
            points = re.split(r"(?m)^### (.+)\n", body)
            if len(points) < 3:
                errors.append(f"{item['name']}/{title}：缺少知识点")
            for point, detail in zip(points[1::2], points[2::2]):
                cards += 1
                for marker, label in (("🔴", "核心知识"), ("🔵", "方法与例题"), ("⚫", "易混易错")):
                    matches = re.findall(rf"(?m)^- {marker} \*\*{label}\*\*：(.+)$", detail)
                    if len(matches) != 1 or len(matches[0]) < 25:
                        errors.append(f"{item['name']}/{point}：{label}缺失、重复或仅有短标签")
    reference_ids = [ref["id"] for ref in guide["references"]]
    if len(set(reference_ids)) != len(reference_ids):
        errors.append("课程参考资料ID重复")
    for course in guide["courses"]:
        if not course["group"] or not course["focus"] or not course["depth"]:
            errors.append(f"{course['name']}：缺少范围或深度")
        if set(course["references"]) - set(reference_ids):
            errors.append(f"{course['name']}：参考资料ID不存在")
    for ref in guide["references"]:
        if not ref["url"].startswith("https://") or not ref["use"]:
            errors.append(f"课程参考资料无效：{ref['id']}")
    ids = set()
    for source in exams["sources"]:
        if source["id"] in ids:
            errors.append(f"考情ID重复：{source['id']}")
        ids.add(source["id"])
        for key in ("title", "url", "kind", "applies_to", "finding", "limit"):
            if not source.get(key):
                errors.append(f"{source['id']}：缺少{key}")
        if not source["url"].startswith("https://"):
            errors.append(f"{source['id']}：来源链接无效")
        parts = source["written_parts"]
        if parts is not None and (not parts or any(not isinstance(v, (int, float)) or not 0 <= v <= 100 for v in parts.values()) or abs(sum(parts.values()) - 100) > 0.01):
            errors.append(f"{source['id']}：笔试各部分占比不是有效的百分比")
        if source["professional_subject_weights"] is not None:
            errors.append(f"{source['id']}：当前只有公告/岗位表，专业内部分值需先增加可核验试卷或大纲记录")
    if exams["subject_weights"] is not None:
        errors.append("尚未建立逐题分值依据，不能发布全省专业科目占比")
    if exams["complete_paper_count"] != 0:
        errors.append("完整试卷数量与当前仅含公告的资料集不符")
    regions = {"长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底", "湘西"}
    if set(exams["coverage"]) != regions:
        errors.append("考情覆盖表没有完整列出14个市州")
    return errors, len(notes), chapters, cards, len(exams["sources"])


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        errors, courses, chapters, cards, sources = validate()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"内容校验失败：{exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"校验通过：{courses}科、{chapters}章、{cards}组重点；讲义章节对应有效，{sources}条考情记录明确适用范围与限制。")
    print("这是结构与依据字段校验，不代表已完成全部知识点的教材级准确性审查。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
