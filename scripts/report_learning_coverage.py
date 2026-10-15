"""Write the internal coverage report for course topics and question types."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "audit_reports" / "learning_coverage.md"

OBJECTIVE_TYPES = {"单选", "多选", "判断"}
APPLICATION_ABILITIES = {"场景选型", "读图排障", "过程描述", "代码编写", "SQL编写"}


def current_forms(items):
    forms = []
    if any(
        question.get("type") in OBJECTIVE_TYPES
        or (question.get("type") == "填空" and question.get("ability") in {"概念识记", "比较辨析", "机制解释"})
        for question in items
    ):
        forms.append("客观辨析")
    if any(question.get("type") == "简答" for question in items):
        forms.append("简答说明")
    if any(question.get("ability") == "直接计算" and question.get("type") in {"填空", "简答"} for question in items):
        forms.append("直接计算")
    if any(question.get("type") == "简答" and question.get("ability") in APPLICATION_ABILITIES for question in items):
        forms.append("综合应用")
    if any(question.get("ability") in {"程序阅读", "代码编写", "SQL编写"} for question in items):
        forms.append("代码/语句")
    return forms


def main():
    learning = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    lines = [
        "# 课程知识点、例题与练习覆盖", "",
        "该报告用于内部建设，不发布到学生页面。范围为各高校通用教材共同核心。", "",
        "大学通用教材确定范围，常见期末任务作为解题深度基准；湖南回忆题校准本地题型与情境，408提供相关课程的进阶任务参考。", "",
        "判定方法：按实际题型和作答能力逐项列缺口，不把题量作为完成标准。选择题中的计算只算有提示辨析，不算独立书面计算；计算或代码填空不自动计入概念辨析。代码/语句仍包含阅读与编写，需另看两者数量。", "",
    ]
    all_topic_count = 0
    all_count_ready = 0
    all_form_count = 0
    all_form_ready = 0
    all_tasks = 0
    all_traps = 0
    course_rows = []
    for course in learning["courses"]:
        subjects = set(course.get("subjects", [course["subject"]]))
        items = [question for question in questions if question.get("subject") in subjects]
        topic_counts = Counter(question.get("topic_id") for question in items)
        type_counts = Counter(question.get("type") for question in items)
        short_questions = [question for question in items if question.get("type") == "简答"]
        calculation_questions = [
            question for question in items
            if question.get("ability") == "直接计算" and question.get("type") in {"填空", "简答"}
        ]
        missing = [topic["title"] for topic in course["topics"] if not topic_counts[topic["topic_id"]]]
        topic_items = {topic["topic_id"]: [question for question in items if question.get("topic_id") == topic["topic_id"]] for topic in course["topics"]}
        count_ready = sum(bool(topic_counts[topic["topic_id"]]) for topic in course["topics"])
        form_total = sum(len(topic.get("practice_modes", [])) for topic in course["topics"])
        form_ready = sum(
            len(set(topic.get("practice_modes", [])) & set(current_forms(topic_items[topic["topic_id"]])))
            for topic in course["topics"]
        )
        all_topic_count += len(course["topics"])
        all_count_ready += count_ready
        all_form_count += form_total
        all_form_ready += form_ready
        all_tasks += sum(bool(topic.get("study_task")) for topic in course["topics"])
        all_traps += sum(bool(topic.get("common_trap")) for topic in course["topics"])
        course_rows.append(f"| {course['course_name']} | {len(course['topics'])} | {len(items)} | {sum(question.get('type') in OBJECTIVE_TYPES for question in items)} | {len(short_questions)} | {len(calculation_questions)} | {sum(question.get('ability') == '程序阅读' for question in items)} | {sum(question.get('ability') in {'代码编写', 'SQL编写'} and question.get('type') == '简答' for question in items)} |")
        lines.extend([
            f"## {course['course_name']}", "",
            f"- 题目：{len(items)}",
            f"- 知识点：{len(course['topics'])}，已有练习：{len(course['topics']) - len(missing)}，缺少练习：{len(missing)}",
            f"- 有关联练习：{count_ready}/{len(course['topics'])}；题量不表示考频或教学完整。",
            f"- 练习方式已有对应题：{form_ready}/{form_total}",
            "- 题型：" + "、".join(f"{name}{count}题" for name, count in type_counts.items()),
            f"- 简答核对要点：{sum(bool(question.get('rubric')) for question in short_questions)}/{len(short_questions)}",
            f"- 书面计算核对步骤：{sum(bool(question.get('rubric')) for question in calculation_questions)}/{len(calculation_questions)}",
            "- 缺少练习：" + ("、".join(missing) if missing else "无"), "",
            "| 知识点 | 练习优先级 | 学习层次 | 计划练习方式 | 现有练习方式 | 题量 | 尚缺能力 |",
            "|---|---|---|---|---|---:|---|",
            *[
                "| {title} | {priority} | {steps} | {expected} | {actual} | {count} | {status} |".format(
                    title=topic["title"],
                    priority=topic.get("practice_priority", "正常练"),
                    steps="→".join(topic.get("mastery_steps", ["识别概念"])),
                    expected="、".join(topic.get("practice_modes", ["客观辨析"])),
                    actual="、".join(current_forms(topic_items[topic["topic_id"]])) or "无",
                    count=topic_counts[topic["topic_id"]],
                    status=(
                        "、".join(mode for mode in topic.get("practice_modes", []) if mode not in current_forms(topic_items[topic["topic_id"]])) or "目标方式已有题，仍需教学抽检"
                    ),
                )
                for topic in course["topics"]
            ], "",
        ])
    lines[8:8] = [
        "## 总体结论", "",
        f"- 学习地图知识点：{all_topic_count}；有练习入口：{all_count_ready}。此处不是完整教材节次覆盖证明。",
        f"- 已维护具体闭卷任务：{all_tasks}；从重点卡同步易错边界：{all_traps}。",
        f"- 练习方式已有对应题：{all_form_ready}/{all_form_count}。",
        "- 本报告只统计当前内容分布，不能把网站题量换算为湖南考试课程占比，也不能证明学生会独立作答。", "",
        "## 题库分布与能力结构", "",
        "同一题可能同时是简答和书面计算，下表各能力列不能相加当作总题量。填空单列能力，不强行归入选择判断。", "",
        "| 课程 | 知识点 | 总题量 | 选择判断 | 简答 | 书面计算 | 程序阅读 | 独立代码/SQL编写 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *course_rows, "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {OUTPUT}")


if __name__ == "__main__":
    main()
