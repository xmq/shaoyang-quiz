"""Join full-review receipts without treating structural checks as content proof."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    baseline = read("audit_reports/full_acceptance_baseline.json")
    baseline_ids = set(baseline["question_ids"])
    report_names = [
        "全量验收_题库_2026-10-15.json",
        "全量验收_电子题库_2026-10-15.json",
        "全量验收_核心题库A_2026-10-15.json",
        "全量验收_核心题库B_2026-10-15.json",
    ]
    receipts = []
    for name in report_names:
        payload = read("audit_reports/" + name)
        if isinstance(payload, list):
            rows = payload
        else:
            rows = payload.get("records", payload.get("questions", []))
        receipts.extend({"report": name, "record": row} for row in rows)
    count = Counter(item["record"]["id"] for item in receipts)
    missing = sorted(baseline_ids - set(count))
    duplicate = sorted(qid for qid, number in count.items() if number != 1)
    unknown = sorted(set(count) - baseline_ids)
    if missing or duplicate or unknown:
        raise ValueError(f"Review IDs: missing={missing[:8]}, duplicate={duplicate[:8]}, unknown={unknown[:8]}")

    learning = read("learning-map.json")
    textbooks = {course["name"]: course for course in read("textbook-map.json")["courses"]}
    questions = read("questions.json")
    question_counts = Counter(q["topic_id"] for q in questions)
    matrix = []
    for course in learning["courses"]:
        text = (ROOT / "course_notes" / f"{course['course_name']}.md").read_text(encoding="utf-8")
        parts = re.split(r"(?m)^## (.+)\n", text)
        for index, chapter in enumerate(course["chapters"]):
            title, body = parts[1 + 2 * index:3 + 2 * index]
            if title != chapter["title"]:
                raise ValueError(f"Lecture chapter mismatch: {chapter['chapter_id']}")
            topics = [t for t in course["topics"] if t["chapter_id"] == chapter["chapter_id"]]
            matrix.append({
                "course": course["course_name"], "chapter_id": chapter["chapter_id"], "title": title,
                "textbooks": textbooks[course["course_name"]]["textbooks"],
                "alignment": "按通用教材主线组织的保留学习单元；除网络外存在合并或调序，不冒充教材原始节号",
                "retained_sections": re.findall(r"(?m)^### (.+)$", body),
                "intended_depth": "大学常见期末解题深度：说明概念、执行过程、用对条件、独立完成代表任务、辨别误用",
                "topic_ids": [t["topic_id"] for t in topics],
                "practice": [{"topic_id": t["topic_id"], "modes": t["practice_modes"], "questions": question_counts[t["topic_id"]]} for t in topics],
                "visuals": re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", body),
                "examples": re.findall(r"(?m)^### .*例.*$|<summary>(.*?)</summary>", body),
                "student_evidence": [
                    {"report": "全量验收_新生_2026-10-15.json", "chapter_id": chapter["chapter_id"]},
                    {"report": "全量验收_独立解题_2026-10-15.json", "chapter_id": chapter["chapter_id"]},
                ],
                "evidence_boundary": "两位代理逐章实读、每章各做两题；上述正文节次逐项列出供持续维护，不能由节数或题量推出每一种题型都已覆盖",
            })
    source_files = [ROOT / name for name in ("learning-map.json", "questions.json", "topic-ids.json", "notes.template.html", "app.js", "question-media.js", "style.css", "ui.css", "home.js", "study-review.js", "sw.js")]
    source_files += [p for folder in ("course_notes", "color_notes", "media") for p in (ROOT / folder).glob("*") if p.is_file()]
    source_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    source = json.dumps(source_hashes, sort_keys=True).encode("utf-8")
    payload = {
        "baseline_commit": baseline["baseline_commit"], "baseline_questions": len(baseline_ids),
        "baseline_semantic_reviewed": len(count), "baseline_id_coverage": "complete",
        "current_questions": len(questions), "chapters": len(matrix),
        "topics": sum(len(c["topics"]) for c in learning["courses"]),
        "source_hash": hashlib.sha256(source).hexdigest(),
        "source_files": source_hashes,
        "question_reports": report_names,
        "acceptance_status": "await_final_retests",
        "coverage_matrix": matrix,
    }
    output = ROOT / "audit_reports/full_acceptance_manifest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Full baseline receipts: {len(count)}; chapters: {len(matrix)}; final retests are recorded separately")


if __name__ == "__main__":
    main()
