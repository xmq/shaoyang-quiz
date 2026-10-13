"""Generate the compact question index used by the homepage."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def render():
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    fields = ("id", "subject", "type", "answer")
    index = [{key: item.get(key, "") for key in fields} for item in questions]
    return "globalThis.HOME_QUESTION_INDEX=Object.freeze(" + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ");\n"
