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
    network = json.loads((ROOT / "network-exam-sources.json").read_text(encoding="utf-8"))
    learning_map = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
    if learning_map.get("schema_version") != 3 or not learning_map.get("scope_policy") or not learning_map.get("exam_policy"):
        errors.append("学习地图缺少范围或命题方式说明")
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
        if item["name"] == "计算机网络":
            preface = text.split("## ", 1)[0]
            if len(re.sub(r"\s+|[#*`]", "", preface)) > 80:
                errors.append("计算机网络：重点页前言过长，应直接进入复习卡")
            if text.count("![") < 6:
                errors.append("计算机网络：图解复习卡不足6张")
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
                if item["name"] == "计算机网络":
                    visible = re.sub(r"!\[[^\]]*\]\([^)]+\)|\s+|[*#`🔴🔵⚫-]", "", detail)
                    if len(visible) > 220:
                        errors.append(f"计算机网络/{point}：复习卡超过220字，不符合一屏复习要求")
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
    network_ids = [source["id"] for source in network["sources"]]
    network_titles = re.findall(r"(?m)^### (.+)$", (ROOT / "color_notes" / "计算机网络.md").read_text(encoding="utf-8"))
    mapped_courses = {course["course_name"]: course for course in learning_map["courses"]}
    for note in notes:
        course = mapped_courses.get(note["name"])
        if not course:
            errors.append(f"学习地图缺少课程：{note['name']}")
            continue
        actual_titles = re.findall(r"(?m)^### (.+)$", (ROOT / note["file"]).read_text(encoding="utf-8"))
        expected_titles = [topic["title"] for topic in course["topics"]]
        if actual_titles != expected_titles:
            errors.append(f"{note['name']}：重点卡与learning-map.json知识点不一致")
        for topic in course["topics"]:
            if topic.get("core_status") != "必学":
                errors.append(f"{note['name']}/{topic['title']}：缺少必学标记")
            if topic.get("practice_priority") not in {"优先练", "正常练", "补充练"}:
                errors.append(f"{note['name']}/{topic['title']}：缺少练习优先级")
            if topic.get("target_depth") not in {"识记理解", "直接应用", "综合应用"} or topic.get("depth") != topic.get("target_depth"):
                errors.append(f"{note['name']}/{topic['title']}：掌握深度无效或不同步")
            steps = topic.get("mastery_steps")
            if not isinstance(steps, list) or not steps or steps[0] != "识别概念":
                errors.append(f"{note['name']}/{topic['title']}：缺少连续掌握层次")
            forms = topic.get("practice_modes")
            if not isinstance(forms, list) or "客观辨析" not in forms:
                errors.append(f"{note['name']}/{topic['title']}：缺少练习方式")
            if topic.get("short_answer") != ("简答说明" in (forms or [])):
                errors.append(f"{note['name']}/{topic['title']}：简答标记与练习方式不一致")
    network_course = mapped_courses["计算机网络"]
    mapped_titles = [topic["title"] for topic in network_course["topics"]]
    if network_titles != mapped_titles:
        errors.append("计算机网络重点卡与learning-map.json知识点不一致")
    topic_ids = [topic["topic_id"] for topic in network_course["topics"]]
    if len(topic_ids) != len(set(topic_ids)):
        errors.append("计算机网络topic_id重复")
    if len(network_ids) != len(set(network_ids)):
        errors.append("计算机网络试题来源ID重复")
    if len(network["topics"]) != len({topic["name"] for topic in network["topics"]}):
        errors.append("计算机网络证据知识点重复")
    for source in network["sources"]:
        if not source.get("url", "").startswith("https://") or not source.get("status") or not source.get("limit"):
            errors.append(f"计算机网络试题来源缺少地址或限制：{source['id']}")
        scores = source.get("section_scores")
        if scores is not None and sum(scores.values()) != source.get("total_score"):
            errors.append(f"计算机网络卷面分值不符：{source['id']}")
    for topic in network["topics"]:
        if topic["name"] not in network_titles:
            errors.append(f"计算机网络试题证据没有对应笔记：{topic['name']}")
        for evidence in topic["evidence"]:
            if evidence.get("source") not in network_ids or not evidence.get("items"):
                errors.append(f"计算机网络试题证据缺少有效来源或题号：{topic['name']}")
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
    return errors, len(notes), chapters, cards, len(exams["sources"]), len(network["sources"])


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        errors, courses, chapters, cards, sources, network_sources = validate()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"内容校验失败：{exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"校验通过：{courses}科、{chapters}章、{cards}组重点；讲义章节对应有效，{sources}条湖南考情记录、{network_sources}条网络试题资料明确适用范围与限制。")
    print("这是结构与依据字段校验，不代表已完成全部知识点的教材级准确性审查。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
