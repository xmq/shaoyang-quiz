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
    ("node", "--check", "study-review.js"),
    ("node", "scripts/verify_study_review.cjs"),
    ("node", "scripts/verify_answer_checks.cjs"),
    ("node", "--check", "question-media.js"),
    (sys.executable, "scripts/validate_media_assets.py"),
    ("node", "--check", "sw.js"),
    (sys.executable, "scripts/merge_applied_bank.py", "--check"),
    (sys.executable, "scripts/merge_supplement_bank.py", "--check"),
    (sys.executable, "scripts/merge_university_exam_bank.py", "--check"),
    (sys.executable, "scripts/add_network_questions.py", "--check"),
    (sys.executable, "scripts/merge_course_gap_questions.py", "--check"),
    (sys.executable, "scripts/merge_hunan_recall_questions.py", "--check"),
    (sys.executable, "scripts/apply_explanation_overrides.py", "--check"),
    (sys.executable, "scripts/validate_textbook_structure.py"),
    (sys.executable, "scripts/validate_textbook_coverage.py"),
    (sys.executable, "scripts/validate_textbook_coverage.py", "--course", "计算机组成原理", "--require-complete"),
    (sys.executable, "scripts/build_learning_map.py", "--check"),
    (sys.executable, "scripts/enrich_question_metadata.py", "--check"),
    (sys.executable, "scripts/validate_question_reviews.py"),
    (sys.executable, "scripts/verify_reviewed_examples.py"),
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
    for name in ("questions.json", "manifest.webmanifest", "network-exam-sources.json", "exam-profiles.json", "learning-map.json", "textbook-map.json", "textbook-coverage.json", "topic-ids.json", "staging/topic_assignment_acceptance.json", "staging/reviewed_topic_baseline.json"):
        json.loads((ROOT / name).read_text(encoding="utf-8"))
        print(f"JSON有效：{name}", flush=True)
    for command in COMMANDS:
        print("检查：" + " ".join(str(part) for part in command), flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    print("发布结构与数据检查通过；教材内容完整性以外部覆盖审查的明确结论为准。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
