"""Rebuild maintained banks, reviewed corrections, then derived metadata."""
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STEPS=(
    'merge_course_gap_questions.py',
    'merge_applied_bank.py',
    'merge_supplement_bank.py',
    'merge_university_exam_bank.py',
    'merge_hunan_recall_questions.py',
    'apply_explanation_overrides.py',
    'enrich_question_metadata.py',
    'report_learning_coverage.py',
)


def main():
    for name in STEPS:
        result=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT)
        if result.returncode: return result.returncode
    return 0


if __name__=='__main__': raise SystemExit(main())
