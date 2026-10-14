"""Generate the compact question index used by the homepage."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def render():
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    learning_map = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
    fields = ("id", "subject", "type", "answer")
    index = [{key: item.get(key, "") for key in fields} for item in questions]
    courses = [
        {"name": course["course_name"], "chapter_count": len(course.get("chapters", []))}
        for course in learning_map["courses"]
    ]
    return (
        "globalThis.HOME_QUESTION_INDEX=Object.freeze(" + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ");\n"
        "globalThis.HOME_COURSE_INDEX=Object.freeze(" + json.dumps(courses, ensure_ascii=False, separators=(",", ":")) + ");\n"
    )
