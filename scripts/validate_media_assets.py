"""Validate active question diagrams and prevent unused media from shipping."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ids = {q["id"] for q in json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))}
    text = (ROOT / "question-media.js").read_text(encoding="utf-8")
    media = json.loads(text[text.index("{"):text.rfind("}") + 1])
    if set(media) - ids:
        raise ValueError(f"Inactive question media: {sorted(set(media) - ids)}")
    refs = {item["src"].removeprefix("./") for item in media.values()}
    for folder in ("course_notes", "color_notes"):
        for p in (ROOT / folder).glob("*.md"):
            refs.update(value.removeprefix("../").removeprefix("./") for value in re.findall(r"!\[[^]]*\]\(([^)]+)\)", p.read_text(encoding="utf-8")))
    files = {p.relative_to(ROOT).as_posix() for p in (ROOT / "media").rglob("*") if p.is_file()}
    if refs - files or files - refs:
        raise ValueError(f"Media references: missing={sorted(refs - files)}, unused={sorted(files - refs)}")
    print(f"Referenced media: {len(refs)}; active question diagrams: {len(media)}; missing/unused: 0")


if __name__ == "__main__":
    main()
