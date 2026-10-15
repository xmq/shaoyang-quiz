"""Generate the compact question index used by the homepage."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def render():
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    learning_map = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
    fields = ("id", "subject", "type", "answer", "accepted_answers", "answer_revision")
    index = [{key: item.get(key, "") for key in fields} for item in questions]
    courses = [
        {
            "name": course["course_name"],
            "subject": course["subject"],
            "subjects": course.get("subjects", [course["subject"]]),
            "chapter_count": len(course.get("chapters", [])),
            "review_card_counts": [
                sum(topic["chapter_id"] == chapter["chapter_id"] for topic in course.get("topics", []))
                for chapter in course.get("chapters", [])
            ],
            "priority_topics": [
                topic["topic_id"] for topic in course.get("topics", [])
                if topic.get("practice_priority") == "优先练"
            ],
        }
        for course in learning_map["courses"]
    ]
    return (
        "globalThis.HOME_QUESTION_INDEX=Object.freeze(" + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ");\n"
        "globalThis.HOME_COURSE_INDEX=Object.freeze(" + json.dumps(courses, ensure_ascii=False, separators=(",", ":")) + ");\n"
    )
