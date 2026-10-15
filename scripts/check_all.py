"""Run the single validation gate used by local checks, CI, and deployment."""
from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    ("node", "--check", "app.js"),
    ("node", "--check", "quiz-loader.js"),
    ("node", "--check", "home.js"),
    ("node", "--check", "question-media.js"),
    ("node", "--check", "sw.js"),
    (sys.executable, "scripts/merge_applied_bank.py", "--check"),
    (sys.executable, "scripts/merge_supplement_bank.py", "--check"),
    (sys.executable, "scripts/merge_university_exam_bank.py", "--check"),
    (sys.executable, "scripts/add_network_questions.py", "--check"),
    (sys.executable, "scripts/merge_course_gap_questions.py", "--check"),
    (sys.executable, "scripts/merge_hunan_recall_questions.py", "--check"),
    (sys.executable, "scripts/validate_textbook_structure.py"),
    (sys.executable, "scripts/build_learning_map.py", "--check"),
    (sys.executable, "scripts/enrich_question_metadata.py", "--check"),
    (sys.executable, "scripts/report_learning_coverage.py"),
    (sys.executable, "scripts/validate_color_notes.py"),
    (sys.executable, "scripts/validate_course_notes.py"),
    (sys.executable, "scripts/build_site.py", "--output", "dist"),
    (sys.executable, "scripts/validate_questions.py", "--js", "dist/questions.js"),
    (sys.executable, "scripts/build_release.py", "--asset-root", "dist", "--check"),
    ("node", "--check", "dist/build-meta.js"),
    ("node", "--check", "dist/questions.js"),
)


def main() -> int:
    for name in ("questions.json", "manifest.webmanifest", "network-exam-sources.json", "learning-map.json", "textbook-map.json"):
        json.loads((ROOT / name).read_text(encoding="utf-8"))
        print(f"JSON有效：{name}", flush=True)
    for command in COMMANDS:
        print("检查：" + " ".join(str(part) for part in command), flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    print("全部检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
