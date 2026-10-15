"""Deterministically enrich question-bank items with learning metadata.

The default mode updates questions.json in place.  ``--check`` performs the
same classification in memory and fails when stored metadata is missing or
stale.  ``--dry-run`` only prints the expected distribution.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from add_network_questions import NEW_QUESTIONS


ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"
NETWORK_QUESTIONS = {question["id"]: question for question in NEW_QUESTIONS}
GAP_QUESTIONS = {
    question["id"]: question
    for question in json.loads((ROOT / "staging" / "course_gap_questions.json").read_text(encoding="utf-8"))
}
# The reviewed source banks already assign the ability from the actual task.
# Keep those human labels; apply stem heuristics only to legacy imported items.
MAINTAINED_QUESTIONS = {
    question["id"]: question
    for name in (
        "applied_core_computer.json", "applied_network_application.json", "applied_electronics.json",
        "supplement_core_thin.json", "supplement_electronics_practical.json",
        "university_applied.json", "university_corecs.json", "university_electronics.json",
    )
    for question in json.loads((ROOT / "staging" / name).read_text(encoding="utf-8"))
}
REVIEWED_TOPIC_OVERRIDES = {
    item["id"]: item["topic_id"]
    for item in json.loads((ROOT / "staging" / "topic_override_review_other.json").read_text(encoding="utf-8"))
}
LEARNING_MAP = json.loads((ROOT / "learning-map.json").read_text(encoding="utf-8"))
COURSE_BY_SUBJECT = {
    subject: course
    for course in LEARNING_MAP["courses"]
    for subject in course.get("subjects", [course["subject"]])
}
NETWORK_COURSE = next(course for course in LEARNING_MAP["courses"] if course["subject"] == "计算机网络")
NETWORK_TOPICS = tuple(NETWORK_COURSE["topics"])
NETWORK_TOPIC_BY_ID = {topic["topic_id"]: topic for topic in NETWORK_TOPICS}

# 旧题题干过短或包含跨层术语时，关键词分类会把首题放到错误专题。
# 这里只保留能够从题干解题任务直接确认的覆盖。
NETWORK_TOPIC_OVERRIDES = {
    "cg-08-s1-q13": "net.frames-switching",
    "zg-55249": "net.overview",
    "zg-61952": "net.dns-dhcp",
    "cg-08-s1-q30": "net.flow-congestion",
    "cg-08-s1-q8": "net.overview",
    "cg-08-s1-q96": "net.ethernet-wifi",
    "cg-08-s1-q27": "net.tcp-udp",
    "cg-08-s1-q102": "net.http",
    "cg-08-s1-q35": "net.media",
    "cg-08-s1-q28": "net.crypto-signature",
    "cg-08-s1-q12": "net.routing",
    "cg-08-s1-q15": "net.overview",
    "zg-33738": "net.media",
    "cg-08-s1-q103": "net.app-protocols",
    "cg-08-s1-q36": "net.app-protocols",
    "zg-66746": "net.layers-addresses",
    "cg-08-s1-q104": "net.app-protocols",
    "cg-08-s1-q39": "net.tcp-udp",
    "web-27": "net.routing",
    "dy-be79e543": "net.overview",
    "dy-3bb220bd": "net.overview",
    "zg-53166": "net.overview",
    "zg-43176": "net.overview",
    "dy-c5d3ca69": "net.app-protocols",
    "uf-nw-005": "net.tcp-connection",
    "ap-nw-004": "net.layers-addresses",
}

# 题干过短或术语跨主题时，明确指定其实际解题任务。
DATABASE_TOPIC_OVERRIDES = {
    "cg-09-s1-q14": 4, "cg-09-s1-q17": 11, "cg-09-s1-q20": 1,
    "cg-09-s1-q21": 1, "cg-09-s1-q23": 4, "cg-09-s1-q28": 2,
    "cg-09-s1-q30": 1, "cg-09-s1-q31": 1, "cg-09-s1-q36": 6,
    "cg-09-s1-q45": 6, "cg-09-s1-q49": 6, "cg-09-s1-q50": 6,
    "cg-09-s1-q53": 6, "cg-09-s1-q60": 5, "cg-09-s1-q62": 7,
    "cg-09-s1-q65": 17, "cg-09-s1-q67": 1, "cg-09-s2-q1": 6,
    "zg-79633": 4, "zg-91256": 4, "zg-5594": 4, "zg-41008": 6,
    "zg-25661": 4, "zg-27720": 6, "zg-75617": 1, "zg-5212": 7,
    "zg-77676": 4, "zg-24086": 4, "zg-25187": 6,
    "uf-db-005": 13, "uc-db-002": 8, "uc-db-003": 13,
    "uc-db-010": 7, "ap-db-003": 15,
}

PROGRAMMING_TOPIC_OVERRIDES = {
    "zg-73534": 5, "cg-04-s1-q6": 4, "cg-04-s1-q8": 6,
    "cg-04-s1-q9": 6, "cg-04-s1-q13": 7, "cg-04-s3-q1": 1,
    "cg-04-s3-q6": 1, "cg-04-s2-q4": 1, "cg-04-s1-q14": 7,
    "cg-04-s2-q5": 4, "uf-pl-001": 4, "ua-program-009": 8,
    "uf-pl-004": 8, "uf-pl-005": 12, "ua-program-004": 12,
    "ua-program-005": 8, "ua-program-012": 11,
    "cg-04-s2-q7": 11, "cg-04-s2-q8": 11, "cg-04-s2-q10": 11, "zg-1554": 6,
    "ap-pl-001": 12, "ua-program-006": 11, "ua-program-013": 10,
    "hn-recall-cs25-001": 14,
    "uf-pl-006": 1, "gap-pl-002": 5,
}

COURSE_TOPIC_OVERRIDES = {
    "办公软件": {
        "cg-11-s1-q5": 1, "cg-11-s1-q11": 3, "cg-11-s1-q43": 3,
        "cg-11-s1-q55": 6, "cg-11-s1-q72": 17,
        "cg-11-s1-q38": 6, "cg-12-s1-q12": 8,
        "cg-11-s1-q70": 3, "cg-11-s2-q8": 3,
        "cg-11-s2-q14": 6, "cg-12-s1-q20": 8,
        "cg-12-s1-q10": 8, "cg-12-s1-q3-dup2": 15,
        "cg-12-s1-q5-dup2": 15,
        "web-28": 5, "cg-13-s1-q11": 6, "cg-13-s1-q31": 6,
        "cg-12-s1-q3": 8, "cg-12-s1-q18": 8, "cg-13-s1-q38": 8,
        "cg-13-s1-q43": 8, "cg-13-s1-q65": 8, "ua-office-015": 11,
        "ap-of-006": 17,
    },
    "多媒体": {
        "cg-02-s2-q13": 9, "cg-02-s2-q9": 14, "cg-02-s2-q15": 4,
        "dy-e77f3198": 4, "dy-d93b9d22": 7, "dy-0bd8dc94": 7,
        "dy-fa7fa77f": 9, "dy-1a9b3e74": 9, "zg-39584": 4,
        "ap-mm-004": 4, "ua-media-004": 4, "ua-media-008": 11,
        "cg-02-s3-q2": 3, "cg-14-s1-q46": 10,
    },
    "算法与数据结构": {
        "cg-05-s1-q12": 1, "cg-05-s1-q33": 9,
        "cg-05-s1-q45": 1, "zg-65564": 1, "ap-ds-005": 24,
        "cg-05-s1-q29": 5, "zg-97573": 1,
        "ap-ds-001": 2, "ap-ds-004": 24, "uc-ds-010": 24,
        "cg-05-s1-q7": 1, "cg-05-s1-q34": 1,
    },
    "操作系统": {
        "cg-10-s1-q34": 9, "cg-10-s1-q41": 9, "dy-3d38882f": 9,
    },
    "电路分析与电工技术": {
        "uf-ee-018": 6, "uf-ee-019": 7, "uf-ee-020": 7,
        "uf-ee-023": 9, "uf-ee-024": 8, "ue-circuit-014": 5,
        "sp-elec-circuit-001": 11, "sp-elec-circuit-002": 11,
        "sp-elec-circuit-020": 11, "sp-elec-circuit-021": 11,
        "sp-elec-circuit-026": 11, "sp-elec-circuit-011": 12,
        "sp-elec-circuit-012": 12, "sp-elec-circuit-014": 12,
        "sp-elec-circuit-019": 12, "sp-elec-circuit-023": 12,
        "sp-elec-circuit-025": 12, "sp-elec-circuit-027": 12,
        "sp-elec-circuit-030": 12,
    },
    "模拟电子技术": {
        "uf-ae-005": 3, "sp-elec-analog-013": 1,
        "sp-elec-analog-014": 10, "sp-elec-analog-016": 10,
        "sp-elec-analog-017": 10, "ue-analog-002": 3,
        "ue-analog-001": 2, "ue-analog-004": 4, "ue-analog-015": 3,
        "uf-ae-017": 6, "uf-ae-018": 6, "uf-ae-019": 6,
        "uf-ae-024": 10, "ap-analog-004": 6,
        "sp-elec-analog-010": 10, "sp-elec-analog-011": 10,
        "sp-elec-analog-012": 10,
        "sp-elec-analog-019": 10, "sp-elec-analog-020": 10,
        "sp-elec-analog-025": 10, "sp-elec-analog-026": 10,
        "sp-elec-analog-029": 10, "sp-elec-analog-030": 10,
    },
    "数字电子技术": {
        "uf-de-021": 8,
        "sp-elec-digital-002": 2, "sp-elec-digital-003": 10,
        "sp-elec-digital-028": 10, "sp-elec-digital-011": 11,
        "sp-elec-digital-012": 11, "sp-elec-digital-018": 11,
        "sp-elec-digital-024": 11, "sp-elec-digital-025": 11,
        "sp-elec-digital-029": 11, "sp-elec-digital-030": 11,
        "ap-digital-006": 10,
    },
    "通信原理与高频电子线路": {
        "sp-elec-comm-004": 11,
        "uf-cm-003": 2, "uf-cm-020": 11, "ap-comm-002": 6,
        "ue-comm-001": 11, "ue-comm-006": 5, "ue-comm-008": 9, "ue-comm-009": 9,
        "sp-elec-comm-005": 12,
        "sp-elec-comm-006": 12, "sp-elec-comm-007": 12,
        "sp-elec-comm-015": 12, "sp-elec-comm-016": 12,
        "sp-elec-comm-021": 12, "sp-elec-comm-026": 12,
        "sp-elec-comm-008": 13, "sp-elec-comm-009": 14,
        "sp-elec-comm-017": 13, "sp-elec-comm-019": 13,
        "sp-elec-comm-020": 14, "sp-elec-comm-023": 13,
        "sp-elec-comm-027": 14, "sp-elec-comm-028": 14,
        "sp-elec-comm-011": 15, "sp-elec-comm-012": 15,
        "sp-elec-comm-013": 15, "sp-elec-comm-014": 15,
        "sp-elec-comm-018": 16, "sp-elec-comm-022": 16,
        "sp-elec-comm-029": 16, "sp-elec-comm-030": 16,
        "gap-comm-002": 16,
    },
    "信号与系统": {
        "gap-signal-007": 13,
    },
    "信息安全": {
        "zg-56133": 3, "zg-20143": 3, "zg-18084": 2,
    },
}


SUBJECT_OVERRIDES = {
    "zg-4542": "算法与数据结构",
    "cg-04-s1-q16": "算法与数据结构",
    "cg-06-s1-q5": "软件工程", "cg-06-s1-q8": "软件工程",
    "cg-06-s1-q9": "软件工程", "cg-06-s1-q10": "软件工程",
    "cg-06-s1-q12": "软件工程", "cg-06-s1-q13": "软件工程",
    "cg-06-s1-q14": "软件工程", "cg-06-s1-q15": "软件工程",
    "cg-06-s1-q16": "软件工程", "cg-06-s1-q17": "软件工程",
    "cg-06-s1-q18": "软件工程", "cg-06-s2-q1": "软件工程",
    "cg-06-s1-q6": "软件工程", "cg-06-s1-q7": "软件工程",
    "dy-6ff41d09": "操作系统", "dy-ebc6d4f4": "操作系统",
    "zg-32499": "操作系统", "dy-e43d68bb": "操作系统",
    "dy-bd96ef41": "操作系统", "dy-ca4e8ea5": "操作系统",
    "dy-d9f15556": "操作系统", "dy-3d38882f": "操作系统",
    "dy-58750fc1": "操作系统",
    "cg-02-s4-q28": "多媒体", "cg-02-s4-q29": "多媒体",
    "cg-02-s4-q30": "多媒体", "zg-53822": "多媒体",
    "cg-06-s1-q11": "软件工程",
    "dy-cad45571": "办公软件", "dy-ceb37dcf": "办公软件",
}

COMPUTER_ORGANIZATION_TOPIC_OVERRIDES = {
    "uf-co-003": 9, "ap-co-004": 9, "sp-core-co-024": 9,
    "sp-core-co-004": 6, "sp-core-co-006": 7, "sp-core-co-019": 1,
    "uf-co-005": 7, "sp-core-co-002": 3, "sp-core-co-001": 2,
}

SOFTWARE_ENGINEERING_TOPIC_OVERRIDES = {
    "uf-se-001": 3, "uf-se-006": 13, "ap-se-001": 3, "ap-se-004": 15,
    "sp-core-se-005": 13, "sp-core-se-022": 6, "se-gen-q02": 6,
    "se-gen-q04": 9, "uf-se-003": 9, "sp-core-se-025": 5,
    "sp-core-se-031": 15, "se-gen-q06": 12, "sp-core-se-001": 6,
    "sp-core-se-004": 11, "uf-se-007": 14, "ap-se-003": 4,
    "sp-core-se-029": 13, "uc-se-008": 16, "uc-se-015": 17,
    "se-gen-q13": 16, "sp-core-se-006": 2, "gap-se-005": 9,
    "se-gen-q11": 15, "cg-06-s1-q5": 5, "cg-06-s1-q8": 15,
    "cg-06-s1-q9": 10, "cg-06-s1-q10": 9, "cg-06-s1-q12": 6,
    "cg-06-s1-q13": 8, "cg-06-s1-q14": 15, "cg-06-s1-q15": 13,
    "cg-06-s1-q16": 13, "cg-06-s1-q17": 11, "cg-06-s1-q18": 14,
    "cg-06-s2-q1": 2, "cg-06-s1-q7": 6,
    "cg-06-s1-q6": 6, "cg-06-s1-q11": 7,
}

INFORMATION_SECURITY_TOPIC_OVERRIDES = {
    "cg-02-s5-q10": 5, "cg-02-s5-q31": 4, "zg-67463": 4,
    "zg-86566": 9, "dy-ed4ba4a8": 11, "dy-fc9c9344": 12,
    "ua-security-008": 13, "zg-99117": 6, "ua-security-013": 11,
    "cg-02-s5-q34": 6, "uf-is-008": 14, "dy-a49aea0d": 1,
    "ap-is-001": 6, "ap-is-005": 15, "gap-sec-001": 2,
    "ap-is-003": 4, "ua-security-007": 11,
    "cg-02-s5-q36": 17, "cg-02-s5-q38": 17, "zg-87787": 17,
    "zg-64566": 17, "cg-02-s5-q42": 4, "dy-f0bf2432": 4,
    "dy-8307738b": 5, "zg-15807": 11, "ua-security-001": 1,
    "cg-02-s5-q41": 17, "dy-bbde8ae8": 17, "dy-7f065639": 6,
    "dy-254e4516": 3, "cg-02-s5-q24": 11,
    "dy-c5f2395e": 2, "dy-06eb99e1": 2,
    "zg-61071": 3,
}

COMPUTER_FOUNDATION_TOPIC_OVERRIDES = {
    "gap-found-012": 20, "gap-found-013": 17, "gap-found-014": 3,
    "gap-found-015": 7, "gap-found-016": 18,
    "hn-recall-hn26-019": 5, "dy-d0f42341": 1,
    "cg-06-s1-q110": 4, "cg-06-s1-q113": 4, "cg-06-s2-q14": 5,
    "zg-11096": 7, "zg-10890": 5, "zg-13337": 7,
    "dy-787d8c1c": 7, "dy-d9f15556": 7, "bd-004": 11,
    "cg-02-s4-q29": 18, "cg-02-s4-q8": 1, "cg-06-s2-q11": 5,
    "zg-34499": 5, "dy-a34990fe": 18, "bd-012": 10,
    "cg-06-s1-q7-dup2": 5, "cg-06-s1-q53": 5, "cg-06-s1-q55": 4,
    "cg-06-s1-q56": 4, "cg-06-s1-q57": 5, "cg-06-s1-q59": 5,
    "cg-06-s1-q71": 7, "cg-06-s1-q73": 7, "cg-06-s1-q75": 7,
    "cg-06-s1-q79": 5, "cg-06-s1-q82": 3, "cg-06-s1-q85": 5,
    "cg-06-s1-q92": 5, "cg-06-s1-q109": 4, "cg-06-s1-q115": 4,
    "cg-06-s1-q120": 4, "cg-06-s1-q123": 5, "cg-06-s1-q124": 7,
    "cg-06-s1-q125": 8, "cg-06-s1-q127": 7, "cg-06-s2-q9": 5,
    "zg-89812": 7, "zg-48939": 12, "zg-14524": 12, "zg-35316": 6,
    "zg-34558": 5, "dy-b94730f1": 5, "dy-80d7632d": 5,
    "dy-afba316e": 5, "dy-cad45571": 7, "dy-054f157b": 3,
    "dy-bd550aaa": 4, "dy-61f909a0": 5, "dy-e4ba04f5": 12,
    "dy-a9948f58": 19, "dy-debdaa71": 5, "dy-5ae4aebc": 4,
    "dy-ea8b6f42": 5, "dy-ceb37dcf": 7, "dy-045071ea": 5,
    "dy-a330b096": 1, "dy-2435453e": 4, "dy-8c289d6a": 5,
    "dy-dcc5d2d0": 18, "dy-fb0af697": 5, "dy-ed0b8d0c": 18,
    "dy-f55f74f2": 7, "dy-ae13649a": 5, "dy-12ac6095": 7,
    "cg-02-s1-q29": 18, "cg-02-s1-q33": 14, "cg-02-s1-q39": 14,
    "cg-02-s4-q2": 1, "cg-02-s4-q5": 1, "cg-02-s4-q7": 1,
    "cg-02-s4-q9": 1, "cg-02-s4-q10": 1, "cg-02-s4-q12": 18,
    "cg-02-s4-q13": 12, "cg-02-s4-q15": 12, "cg-02-s4-q17": 18,
    "cg-02-s4-q18": 12, "cg-02-s4-q23": 14, "cg-02-s4-q24": 14,
    "cg-02-s4-q34": 4, "cg-06-s1-q14-dup2": 5,
    "zg-7462": 1, "zg-71472": 1, "zg-39116": 1, "zg-63645": 19,
    "zg-96001": 4, "zg-99635": 1, "zg-98060": 1, "zg-53822": 18,
    "web-15": 1, "web-39": 18, "dy-335e6a07": 5, "dy-94760839": 5,
    "dy-c8552785": 12, "dy-1df18068": 19,
    "gap-found-005": 8, "cg-06-s1-q91": 3, "zg-82870": 3,
    "dy-2987416e": 3, "zg-68914": 4, "zg-76959": 4, "zg-68489": 4,
    "zg-75106": 1, "zg-21588": 1, "dy-fc9f80bb": 7,
    "zg-11096": 1, "zg-98509": 18, "cg-06-s1-q37": 5,
    "cg-06-s1-q41": 5, "cg-06-s1-q50": 5, "cg-06-s2-q12": 5,
    "dy-db4045b7": 5, "zg-32272": 7, "zg-91871": 7,
    "zg-24227": 7, "cg-06-s1-q72": 7, "cg-02-s1-q39": 1,
    "zg-37965": 5, "cg-06-s1-q27": 5, "cg-06-s1-q29": 5,
    "cg-06-s1-q60": 5, "cg-06-s1-q65": 5, "cg-06-s2-q13": 5,
    "web-5": 5, "dy-066977aa": 5, "dy-24ad9ede": 5,
    "dy-ff93663e": 5, "dy-963a7c67": 5, "dy-62555133": 5,
    "dy-80efea9a": 5, "cg-06-s1-q87": 3, "cg-06-s1-q88": 3,
    "dy-2ebd08bc": 3, "cg-06-s1-q108": 4, "dy-1b6211b9": 4,
    "zg-95580": 18, "dy-0574dff5": 18, "dy-60fa8fa5": 12,
    "cg-06-s1-q107": 4, "cg-06-s1-q117": 4, "cg-06-s1-q121": 4,
    "dy-9b84fc08": 4, "dy-580bc45f": 4, "dy-85006573": 1,
    "cg-06-s1-q118": 4,
    "cg-06-s1-q17-dup2": 5, "cg-06-s1-q64": 5, "web-7": 4,
    "cg-06-s1-q70": 5, "cg-06-s1-q77": 3, "cg-06-s2-q22": 4,
}

REMOVED_QUESTION_IDS = {
    "zg-6305", "dy-a34a3129", "dy-ae14613b",
    "zg-84677", "zg-84991", "zg-88625", "zg-92120", "dy-47c582f3",
    "cg-02-s5-q44", "dy-4adfd2a8", "cg-02-s5-q10", "cg-02-s5-q8",
    "dy-329ccda4", "dy-ce04a943", "dy-c908dd34", "zg-77636", "dy-ed4ba4a8",
    "cg-02-s5-q36", "cg-02-s5-q38", "zg-87787", "zg-64566",
    "bd-014",
    "zg-21718", "zg-49738", "zg-20789", "cg-02-s5-q42",
    "cg-02-s5-q13", "cg-02-s5-q37", "dy-f7dba4a4", "zg-26051",
    "zg-48687", "uf-is-002",
    "cg-06-s1-q8",
    "bd-003", "bd-004", "bd-005", "bd-006", "bd-007", "bd-008",
    "bd-009", "bd-010", "bd-012", "bd-013", "bd-015",
    "cg-02-s4-q24", "dy-1e0130fb", "cg-02-s4-q12",
    "cg-06-s1-q126", "dy-dcc5d2d0", "cg-02-s4-q31", "cg-02-s4-q33",
    "zg-63645", "dy-a9948f58", "dy-1df18068",
    "cg-02-s5-q45",
    "bd-011", "cg-06-s1-q124", "cg-06-s1-q127", "dy-b1fdb3e1",
    "cg-06-s1-q57", "dy-80d7632d", "dy-afba316e", "dy-1057d716",
    "dy-debdaa71", "zg-91871", "zg-24227", "dy-0fdc6c59",
    "zg-68262", "cg-06-s2-q22",
    # 微控制器、总线与现场调试属于数字系统接口专题，不纳入通用数电核心。
    "sp-elec-digital-001", "sp-elec-digital-004", "sp-elec-digital-005",
    "sp-elec-digital-006", "sp-elec-digital-007", "sp-elec-digital-008",
    "sp-elec-digital-009", "sp-elec-digital-010", "sp-elec-digital-013",
    "sp-elec-digital-014", "sp-elec-digital-015", "sp-elec-digital-016",
    "sp-elec-digital-017", "sp-elec-digital-019", "sp-elec-digital-020",
    "sp-elec-digital-021", "sp-elec-digital-022", "sp-elec-digital-023",
    "sp-elec-digital-026", "sp-elec-digital-027",
}

REMOVED_LEGACY_COURSE_IDS = {
    'cg-02-s2-q6', 'cg-02-s2-q8', 'cg-02-s3-q4', 'cg-02-s3-q5', 'cg-11-s1-q20',
    'cg-11-s1-q22', 'cg-11-s1-q23', 'cg-11-s1-q33', 'cg-11-s1-q37', 'cg-11-s1-q52',
    'cg-11-s1-q6', 'cg-11-s1-q69', 'cg-12-s1-q11', 'cg-12-s1-q11-dup2', 'cg-12-s1-q13-dup2',
    'cg-12-s1-q15-dup2', 'cg-12-s1-q20-dup2', 'cg-12-s1-q21-dup2', 'cg-12-s1-q26-dup2', 'cg-12-s1-q3',
    'cg-12-s1-q36', 'cg-12-s1-q54', 'cg-12-s1-q72', 'cg-12-s1-q8-dup2', 'cg-12-s2-q11-dup2',
    'cg-13-s1-q10-dup2', 'cg-13-s1-q12', 'cg-13-s1-q12-dup2', 'cg-13-s1-q13-dup2', 'cg-13-s1-q14-dup2',
    'cg-13-s1-q15-dup2', 'cg-13-s1-q16-dup2', 'cg-13-s1-q17', 'cg-13-s1-q18-dup2', 'cg-13-s1-q19-dup2',
    'cg-13-s1-q20-dup2', 'cg-13-s1-q23', 'cg-13-s1-q23-dup2', 'cg-13-s1-q24-dup2', 'cg-13-s1-q26-dup2',
    'cg-13-s1-q28', 'cg-13-s1-q28-dup2', 'cg-13-s1-q31-dup2', 'cg-13-s1-q32-dup2', 'cg-13-s1-q35-dup2',
    'cg-13-s1-q36-dup2', 'cg-13-s1-q38-dup2', 'cg-13-s1-q42-dup2', 'cg-13-s1-q43-dup2', 'cg-13-s1-q45',
    'cg-13-s1-q45-dup2', 'cg-13-s1-q46-dup2', 'cg-13-s1-q47-dup2', 'cg-13-s1-q48-dup2', 'cg-13-s1-q49-dup2',
    'cg-13-s1-q5-dup2', 'cg-13-s1-q51-dup2', 'cg-13-s1-q54-dup2', 'cg-13-s1-q55', 'cg-13-s1-q57-dup2',
    'cg-13-s1-q58-dup2', 'cg-13-s1-q59-dup2', 'cg-13-s1-q6-dup2', 'cg-13-s1-q68', 'cg-13-s1-q70',
    'cg-13-s1-q72', 'cg-13-s1-q73', 'cg-13-s1-q74', 'cg-13-s1-q9', 'cg-13-s1-q9-dup2',
    'cg-13-s2-q6', 'cg-13-s2-q8', 'cg-13-s2-q9', 'cg-14-s1-q1', 'cg-14-s1-q16',
    'cg-14-s1-q19', 'cg-14-s1-q2', 'cg-14-s1-q29', 'cg-14-s1-q30', 'cg-14-s1-q31',
    'cg-14-s1-q37', 'cg-14-s1-q38', 'cg-14-s1-q41', 'cg-14-s1-q42', 'cg-14-s1-q43',
    'cg-14-s1-q46', 'cg-14-s1-q5', 'cg-14-s2-q3', 'cg-14-s2-q4', 'cg-14-s2-q5',
    'cg-14-s2-q6', 'cg-14-s2-q8', 'dy-0bd8dc94', 'dy-0ebf6e71', 'dy-10b6e8e8',
    'dy-188ea520', 'dy-1d579f68', 'dy-21546db0', 'dy-24fdeec6', 'dy-2ad8e253',
    'dy-2d94b71f', 'dy-361ee2ae', 'dy-451726e5', 'dy-536d6820', 'dy-584a2e52',
    'dy-5d7db5e4', 'dy-6ce6f7cc', 'dy-8ef348fc', 'dy-981d49ba', 'dy-aa301b99',
    'dy-c4ba7b78', 'dy-d05820ee', 'dy-d93b9d22', 'dy-f282e911', 'dy-fa96ac76',
    'dy-fb2048c1', 'web-17', 'zg-16318', 'zg-27203', 'zg-2876',
    'zg-33638', 'zg-36807', 'zg-41643', 'zg-47150', 'zg-50161',
    'zg-53795', 'zg-57642', 'zg-6041', 'zg-63177', 'zg-64787',
    'zg-67040', 'zg-74856', 'zg-75558', 'zg-79192', 'zg-8100',
    'zg-89154', 'zg-96441', 'zg-97108', 'zg-97592', 'zg-99167',
    'zg-9989',
}

REMOVED_OLD_OFFICE_VERSION_IDS = {
    'cg-11-s1-q10', 'cg-11-s1-q14', 'cg-11-s1-q15', 'cg-11-s1-q24', 'cg-11-s1-q25',
    'cg-11-s1-q27', 'cg-11-s1-q29', 'cg-11-s1-q39', 'cg-11-s1-q40', 'cg-11-s1-q64',
    'cg-11-s1-q8', 'cg-12-s1-q13', 'cg-12-s1-q15', 'cg-12-s1-q16', 'cg-12-s1-q18',
    'cg-12-s1-q18-dup2', 'cg-12-s1-q19-dup2', 'cg-12-s1-q22', 'cg-12-s1-q25', 'cg-12-s1-q27',
    'cg-12-s1-q28', 'cg-12-s1-q38', 'cg-12-s1-q5', 'dy-76176218', 'zg-12274',
    'zg-18377', 'zg-21745', 'zg-34814', 'zg-36873', 'zg-65377',
    'zg-68421', 'zg-82387', 'zg-83962', 'zg-84092', 'zg-86151',
}

REMOVED_OLD_MEDIA_PRODUCT_IDS = {
    "zg-61618", "zg-71238", "dy-05a4c679",
}
REMOVED_OFFICE_UI_TRIVIA_IDS = {
    "cg-11-s1-q9", "cg-11-s1-q18", "cg-11-s1-q19", "cg-11-s1-q36",
    "cg-11-s1-q59", "cg-11-s1-q66", "cg-12-s2-q10", "cg-12-s2-q11",
    "cg-12-s1-q9-dup2", "cg-12-s1-q27-dup2", "cg-12-s2-q7-dup2",
    "cg-12-s2-q9-dup2", "cg-13-s1-q3", "cg-13-s1-q4", "cg-13-s1-q5",
    "cg-13-s1-q11", "cg-13-s1-q18", "cg-13-s1-q19", "cg-13-s1-q33",
    "cg-13-s1-q37", "cg-13-s1-q38", "cg-13-s1-q43", "cg-13-s1-q47",
    "cg-13-s1-q48", "cg-13-s1-q49", "cg-13-s1-q56", "cg-13-s1-q58",
    "cg-13-s1-q59", "cg-13-s1-q60", "cg-13-s1-q62", "cg-13-s1-q63",
    "cg-13-s1-q64", "zg-777", "dy-d178b8b9", "dy-8d6ad4e0",
    "dy-deb49e81", "cg-12-s1-q2",
}
ABILITY_VALUES = frozenset({
    "概念识记",
    "比较辨析",
    "直接计算",
    "场景选型",
    "机制解释",
    "过程描述",
    "程序阅读",
    "代码编写",
    "SQL编写",
    "读图排障",
})
DIFFICULTY_VALUES = frozenset({"基础", "应用", "进阶"})


# Rules are ordered from specific to general.  Matching also considers the
# chapter and option text so that generic stems such as “下列说法正确的是”
# still receive a useful knowledge point.
SUBJECT_RULES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "信息基础": (
        ("信息与载体", ("信息载体", "载体", "信息的传递", "信息的表示")),
        ("信息特征", ("信息特征", "共享性", "时效性", "真伪性", "价值性", "依附性")),
        ("信息技术与社会", ("信息技术", "信息社会", "数字鸿沟", "信息化", "知识产权")),
        ("信息素养", ("信息素养", "信息意识", "信息社会责任", "信息伦理")),
    ),
    "计算机基础": (
        ("数制与编码", ("二进制", "十六进制", "八进制", "数制", "ascii", "unicode", "汉字编码", "补码")),
        ("计算机硬件", ("cpu", "中央处理", "运算器", "控制器", "主板", "输入设备", "输出设备", "硬件")),
        ("存储系统", ("内存", "外存", "存储器", "rom", "ram", "硬盘", "u盘", "字节", "容量")),
        ("计算机软件", ("系统软件", "应用软件", "软件系统", "程序设计语言", "语言处理程序")),
        ("计算机发展与应用", ("计算机发展", "计算机特点", "计算机分类", "人工智能", "云计算", "物联网")),
        ("文件与Windows基础", ("文件", "文件夹", "快捷方式", "资源管理器", "windows", "回收站")),
    ),
    "办公软件": (
        ("Excel公式与引用", ("公式", "函数", "sum", "average", "countif", "vlookup", "xlookup", "相对引用", "绝对引用", "单元格引用")),
        ("Excel数据分析", ("排序", "筛选", "分类汇总", "数据透视", "条件格式", "数据验证", "图表")),
        ("Excel工作簿基础", ("excel", "wps表格", "工作簿", "工作表", "单元格", "填充柄")),
        ("Word长文档排版", ("样式", "目录", "题注", "交叉引用", "分节", "页眉", "页脚", "邮件合并", "修订", "批注")),
        ("Word文字与段落", ("word", "wps文字", "字符格式", "段落格式", "首行缩进", "查找替换", "分页符")),
        ("PowerPoint演示", ("powerpoint", "wps演示", "幻灯片", "母版", "版式", "动画", "切换", "放映")),
        ("办公文件与协作", ("office", "wps", "另存为", "自动保存", "pdf", "文件加密", "工作表保护")),
    ),
    "教学论": (
        ("教学评价", ("评价", "信度", "效度", "量规", "测验", "反馈", "诊断性", "形成性", "总结性")),
        ("教学目标与设计", ("教学设计", "教学目标", "学习目标", "学情", "重点", "难点", "教—学—评", "教-学-评")),
        ("教学方法", ("任务驱动", "项目式", "探究学习", "合作学习", "讲授法", "演示练习", "教学方法")),
        ("学习理论", ("行为主义", "认知主义", "建构主义", "人本主义", "最近发展区", "支架")),
        ("课堂组织", ("课堂管理", "上机课", "差异化", "分层任务", "教师作用")),
        ("教学媒体与整合", ("教学媒体", "微课", "翻转课堂", "混合式", "课程整合", "数字资源")),
        ("信息技术课程素养", ("信息意识", "计算思维", "数字化学习", "信息社会责任", "信息技术教育")),
    ),
    "多媒体": (
        ("音频数字化", ("采样", "量化", "pcm", "音频", "声音", "midi", "wav", "mp3", "flac")),
        ("图形图像", ("图像", "图形", "位图", "矢量", "像素", "分辨率", "rgb", "cmyk", "jpeg", "png", "gif", "svg", "photoshop", "ps")),
        ("动画与视频", ("动画", "关键帧", "补间", "flash", "视频", "帧率", "编码器", "容器", "流媒体")),
        ("多媒体压缩与容量", ("压缩", "无损", "有损", "压缩比", "码率", "媒体容量")),
        ("多媒体系统与应用", ("多媒体", "超文本", "超媒体", "媒体类型", "创作工具")),
    ),
    "操作系统": (
        ("进程与线程", ("进程", "线程", "程序与进程", "进程状态", "pcb")),
        ("进程调度与同步", ("调度", "时间片", "信号量", "同步", "互斥", "临界区", "pv操作")),
        ("死锁", ("死锁", "银行家", "安全序列", "请求并保持", "循环等待")),
        ("内存与虚拟存储", ("内存管理", "分页", "分段", "页表", "虚拟存储", "页面置换", "缺页", "抖动")),
        ("文件系统", ("文件系统", "目录结构", "文件分配", "磁盘空间", "文件权限")),
        ("设备与I/O管理", ("设备管理", "spooling", "缓冲", "中断", "i/o", "io设备")),
        ("Windows系统操作", ("windows", "控制面板", "任务管理器", "注册表", "回收站", "资源管理器")),
    ),
    "编程语言": (
        ("C指针与内存", ("指针", "地址运算", "malloc", "free", "动态内存")),
        ("C数组与字符串", ("数组", "字符串", "字符数组", "下标")),
        ("C函数与作用域", ("函数", "形参", "实参", "递归", "作用域", "局部变量", "全局变量")),
        ("C文件与结构体", ("文件操作", "fopen", "fclose", "结构体", "共用体")),
        ("Python数据类型", ("python", "列表", "元组", "字典", "集合", "切片", "可变对象")),
        ("程序控制结构", ("顺序结构", "选择结构", "循环", "if", "for", "while", "break", "continue")),
        ("程序异常与调试", ("异常", "try", "except", "调试", "语法错误", "运行错误")),
        ("程序设计基础", ("算法", "流程图", "伪代码", "程序", "变量", "表达式", "运算符")),
    ),
    "计算机组成原理": (
        ("指令系统与CPU", ("指令", "寻址", "操作码", "cpu", "控制器", "运算器", "寄存器")),
        ("存储层次与Cache", ("cache", "主存", "存储层次", "命中率", "局部性", "虚拟存储器")),
        ("数据表示与运算", ("补码", "浮点", "定点", "溢出", "数据表示", "alu")),
        ("流水线", ("流水线", "数据相关", "控制相关", "结构相关", "加速比")),
        ("总线与I/O", ("总线", "i/o", "io系统", "中断", "dma", "接口")),
        ("计算机系统性能", ("性能", "主频", "cpi", "mips", "吞吐率")),
    ),
    "计算机网络": (
        ("流媒体与服务质量", ("流媒体", "播放缓冲", "rtp", "rtcp", "sip", "qos", "服务质量", "抖动", "自适应码率")),
        ("无线与移动网络", ("无线局域网", "wlan", "wi-fi", "802.11", "csma/ca", "rts/cts", "隐藏站", "ssid", "接入点", "移动ip", "蜂窝网络")),
        ("IPv4与子网", ("ipv4", "ip地址", "子网", "掩码", "网络地址", "广播地址", "cidr", "私有地址", "nat")),
        ("TCP与UDP", ("tcp", "udp", "三次握手", "四次挥手", "序号", "确认", "重传", "滑动窗口", "拥塞")),
        ("DNS与DHCP", ("dns", "dhcp", "域名", "dora", "nslookup", "169.254")),
        ("网络体系结构", ("osi", "tcp/ip", "网络层次", "体系结构", "封装", "协议与服务")),
        ("数据链路与局域网", ("以太网", "mac", "交换机", "vlan", "stp", "crc", "csma", "局域网")),
        ("路由与网络诊断", ("路由", "rip", "ospf", "bgp", "icmp", "arp", "ping", "tracert", "排障")),
        ("应用层协议", ("http", "https", "ftp", "smtp", "pop3", "imap", "ssh", "telnet", "端口")),
        ("物理层与传输介质", ("物理层", "双绞线", "光纤", "无线", "带宽", "时延", "复用", "t568")),
        ("网络设备与拓扑", ("拓扑", "集线器", "路由器", "网关", "ap", "wlan", "ssid")),
    ),
    "数据库": (
        ("数据库安全", ("认证", "授权", "审计", "grant", "revoke", "最小权限", "角色")),
        ("数据库恢复", ("wal", "日志", "检查点", "redo", "undo", "恢复", "备份")),
        ("SQL查询", ("sql", "select", "where", "group by", "having", "join", "查询", "视图")),
        ("事务与并发控制", ("事务", "acid", "并发", "锁", "隔离级别", "提交", "回滚", "死锁")),
        ("关系模型与代数", ("关系模型", "关系代数", "元组", "属性", "主键", "外键", "候选键")),
        ("数据库规范化", ("范式", "规范化", "函数依赖", "1nf", "2nf", "3nf", "bcnf")),
        ("数据库设计", ("e-r", "er图", "概念结构", "逻辑结构", "数据库设计")),
        ("索引与存储", ("索引", "b+树", "聚簇", "存储结构")),
        ("数据库系统基础", ("数据库", "dbms", "数据独立性", "模式", "三级模式")),
    ),
    "算法与数据结构": (
        ("栈与队列", ("栈", "队列", "先进先出", "后进先出")),
        ("图结构与算法", ("图", "顶点", "边", "最短路径", "最小生成树", "深度优先", "广度优先")),
        ("树与二叉树", ("二叉树", "树", "遍历", "哈夫曼", "叶子结点")),
        ("排序算法", ("排序", "冒泡", "插入排序", "快速排序", "归并", "堆排序")),
        ("查找与散列", ("查找", "二分", "折半", "散列", "哈希表")),
        ("线性表", ("线性表", "顺序表", "链表", "数组", "插入", "删除")),
        ("算法复杂度", ("时间复杂度", "空间复杂度", "大o", "算法效率")),
    ),
    "软件工程": (
        ("软件测试", ("测试", "白盒", "黑盒", "单元测试", "集成测试", "系统测试", "边界值", "等价类")),
        ("需求工程", ("需求", "用例", "需求规格", "需求分析", "可追踪")),
        ("软件设计与UML", ("设计", "uml", "类图", "时序图", "模块", "耦合", "内聚")),
        ("软件过程模型", ("瀑布", "原型", "增量", "螺旋", "敏捷", "scrum", "过程模型")),
        ("软件维护与配置", ("维护", "配置管理", "版本控制", "变更管理", "重构")),
        ("项目管理", ("项目管理", "风险管理", "成本", "进度", "甘特图", "关键路径")),
        ("软件工程基础", ("软件危机", "软件工程", "生命周期", "质量保证")),
    ),
    "信息安全": (
        ("安全事件响应", ("事件响应", "应急", "遏制", "根除", "恢复", "复盘", "异常外联", "未授权登录")),
        ("密码技术", ("对称加密", "非对称", "公钥", "私钥", "哈希", "散列", "数字签名", "证书", "base64")),
        ("身份认证与访问控制", ("认证", "授权", "审计", "多因素", "mfa", "访问控制", "最小权限", "rbac")),
        ("恶意代码与社会工程", ("病毒", "蠕虫", "木马", "勒索", "钓鱼", "社会工程", "恶意代码")),
        ("网络安全防护", ("防火墙", "ids", "ips", "vpn", "dmz", "dos", "ddos", "中间人", "欺骗")),
        ("数据备份与恢复", ("备份", "恢复", "raid", "3-2-1", "增量备份", "差异备份")),
        ("安全目标与风险", ("机密性", "完整性", "可用性", "cia", "威胁", "脆弱性", "风险", "等保")),
        ("隐私合规与责任", ("个人信息", "隐私", "法律", "合规", "知识产权")),
    ),
    "大数据": (
        ("Hadoop与HDFS", ("hadoop", "hdfs", "namenode", "datanode", "分布式文件")),
        ("MapReduce与YARN", ("mapreduce", "map", "reduce", "yarn", "resourcemanager")),
        ("Spark", ("spark", "rdd", "弹性分布式")),
        ("数据仓库", ("数据仓库", "olap", "etl", "维度", "事实表")),
        ("流处理", ("流处理", "实时计算", "消息队列")),
        ("大数据基础", ("大数据", "数据处理", "分布式计算")),
    ),
    "电路分析与电工技术": (
        ("直流电路与功率", ("欧姆定律", "基尔霍夫", "串联", "并联", "电阻", "电压", "电流", "功率")),
        ("网络定理", ("叠加定理", "戴维宁", "诺顿", "最大功率传输", "受控源")),
        ("正弦交流与RLC", ("正弦", "相量", "容抗", "感抗", "阻抗", "rlc", "谐振", "功率因数")),
        ("一阶动态电路", ("一阶", "换路", "时间常数", "零输入", "零状态", "暂态")),
        ("三相电路与用电", ("三相", "线电压", "相电压", "星形", "三角形", "安全用电")),
        ("电路可靠性", ("可靠性", "可信度", "失效率")),
    ),
    "模拟电子技术": (
        ("二极管电路", ("二极管", "pn结", "单向导电", "稳压管", "整流")),
        ("三极管放大", ("三极管", "晶体管", "截止", "放大区", "饱和", "共射", "静态工作点")),
        ("MOSFET", ("mosfet", "场效应", "栅极")),
        ("运算放大器", ("运算放大", "运放", "虚短", "虚断", "反相", "同相", "比较器")),
        ("负反馈放大", ("反馈", "闭环增益", "通频带", "失真")),
        ("功率放大", ("功率放大", "甲类", "乙类", "交越失真", "效率")),
        ("直流电源", ("电源", "滤波", "稳压", "桥式整流")),
    ),
    "数字电子技术": (
        ("逻辑代数与门电路", ("逻辑代数", "与门", "或门", "非门", "异或", "卡诺图", "逻辑函数")),
        ("组合逻辑", ("组合逻辑", "编码器", "译码器", "数据选择器", "加法器", "竞争冒险")),
        ("触发器", ("触发器", "rs", "jk", "d触发", "t触发", "状态方程")),
        ("时序逻辑", ("时序逻辑", "计数器", "寄存器", "状态转换", "时钟")),
        ("A/D与D/A转换", ("a/d", "d/a", "adc", "dac", "模数转换", "数模转换")),
        ("脉冲与555电路", ("555", "施密特", "单稳态", "多谐振荡", "脉冲")),
        ("存储与可编程逻辑", ("存储器", "rom", "ram", "pld", "fpga")),
    ),
    "通信原理与高频电子线路": (
        ("通信系统基础", ("通信系统", "信源", "信道", "信宿", "模拟信号", "数字信号", "单工", "半双工", "全双工")),
        ("信道容量与香农公式", ("香农", "信道容量", "信噪比", "奈奎斯特", "带宽")),
        ("模拟调制", ("am", "fm", "pm", "调幅", "调频", "调相", "包络检波", "角度调制")),
        ("数字调制", ("ask", "fsk", "psk", "qam", "数字调制")),
        ("抽样与PCM", ("抽样", "采样定理", "pcm", "量化", "编码")),
        ("复用与线路编码", ("频分复用", "时分复用", "码分复用", "线路编码", "曼彻斯特")),
        ("高频电路", ("高频", "谐振放大", "振荡器", "混频", "超外差", "功率放大器")),
        ("光纤与移动通信", ("光纤", "通信窗口", "移动通信", "1g", "2g", "3g", "4g", "5g")),
    ),
    "信号与系统": (
        ("信号与系统基础", ("周期", "幅度", "能量信号", "功率信号")),
        ("系统性质", ("线性", "时不变", "因果", "稳定")),
        ("LTI系统与卷积", ("冲激响应", "卷积", "lti", "单位冲激")),
        ("频域分析", ("傅里叶", "频谱", "频域")),
        ("拉普拉斯与Z变换", ("拉普拉斯", "z变换", "收敛域", "roc")),
        ("采样定理", ("采样", "抽样", "混叠", "奈奎斯特频率")),
    ),
}

SUBJECT_DEFAULTS = {
    "信息基础": "信息技术与社会",
    "计算机基础": "计算机发展与应用",
    "办公软件": "办公文件与协作",
    "教学论": "信息技术课程素养",
    "多媒体": "多媒体系统与应用",
    "操作系统": "操作系统基础",
    "编程语言": "程序设计基础",
    "计算机组成原理": "计算机组成基础",
    "计算机网络": "计算机网络基础",
    "数据库": "数据库系统基础",
    "算法与数据结构": "数据结构基础",
    "软件工程": "软件工程基础",
    "信息安全": "安全目标与风险",
    "大数据": "大数据基础",
    "电路分析与电工技术": "电路分析基础",
    "模拟电子技术": "模拟电子基础",
    "数字电子技术": "数字电子基础",
    "通信原理与高频电子线路": "通信系统基础",
    "信号与系统": "信号与系统基础",
}

KNOWLEDGE_POINT_VALUES = frozenset(
    {label for rules in SUBJECT_RULES.values() for label, _ in rules}
    | set(SUBJECT_DEFAULTS.values())
    | {"综合基础"}
)


def normalized_text(*values: object) -> str:
    text = " ".join(str(value or "") for value in values)
    return unicodedata.normalize("NFKC", text).lower()


def question_text(
    question: dict,
    *,
    include_options: bool = True,
    include_subject: bool = True,
) -> str:
    values: list[object] = []
    if include_subject:
        values.append(question.get("subject"))
    values.extend([
        question.get("chapter"),
        question.get("source_chapter"),
        question.get("stem"),
    ])
    if include_options:
        options = question.get("options")
        if isinstance(options, dict):
            values.extend(options.values())
    return normalized_text(*values)


NETWORK_TOPIC_FALLBACKS = {
    "IPv4与子网": "net.subnet-routing",
    "TCP与UDP": "net.tcp-udp",
    "DNS与DHCP": "net.dns-dhcp",
    "网络体系结构": "net.layers-addresses",
    "数据链路与局域网": "net.frames-switching",
    "路由与网络诊断": "net.routing",
    "应用层协议": "net.app-protocols",
    "物理层与传输介质": "net.media",
    "网络设备与拓扑": "net.layers-addresses",
    "计算机网络基础": "net.layers-addresses",
}


def classify_network_topic(question: dict) -> dict[str, str]:
    if question.get("topic_source") == "manual" and question.get("topic_id") in NETWORK_TOPIC_BY_ID:
        best = NETWORK_TOPIC_BY_ID[question["topic_id"]]
        return {
            "topic_id": best["topic_id"],
            "topic_title": best["title"],
            "chapter_id": best["chapter_id"],
            "required_depth": best["depth"],
            "topic_order": next(index for index, topic in enumerate(NETWORK_TOPICS) if topic["topic_id"] == best["topic_id"]),
        }
    override_id = NETWORK_TOPIC_OVERRIDES.get(str(question.get("id")))
    if override_id:
        best = NETWORK_TOPIC_BY_ID[override_id]
        return {
            "topic_id": best["topic_id"],
            "topic_title": best["title"],
            "chapter_id": best["chapter_id"],
            "required_depth": best["depth"],
            "topic_order": next(index for index, topic in enumerate(NETWORK_TOPICS) if topic["topic_id"] == best["topic_id"]),
        }
    text = question_text(question)
    best = None
    best_score = (0, 0, -1)
    for index, topic in enumerate(NETWORK_TOPICS):
        matches = [keyword for keyword in topic.get("keywords", []) if normalized_text(keyword) in text]
        score = (max((len(normalized_text(keyword)) for keyword in matches), default=0), len(matches), index)
        if score >= best_score:
            best = topic
            best_score = score
    if best_score[0] == 0:
        topic_id = NETWORK_TOPIC_FALLBACKS.get(str(question.get("knowledge_point") or ""), "net.layers-addresses")
        best = NETWORK_TOPIC_BY_ID[topic_id]
    return {
        "topic_id": best["topic_id"],
        "topic_title": best["title"],
        "chapter_id": best["chapter_id"],
        "required_depth": best["depth"],
        "topic_order": next(index for index, topic in enumerate(NETWORK_TOPICS) if topic["topic_id"] == best["topic_id"]),
    }


def classify_course_topic(question: dict, knowledge_point: str) -> dict[str, str]:
    subject = str(question.get("subject") or "")
    if subject == "计算机网络":
        return classify_network_topic(question)
    course = COURSE_BY_SUBJECT.get(subject)
    if not course or not course.get("topics"):
        return {}
    text = question_text(question)
    topics = list(course["topics"])
    reviewed_topic_id = REVIEWED_TOPIC_OVERRIDES.get(str(question.get("id")))
    reviewed = next((topic for topic in topics if topic["topic_id"] == reviewed_topic_id), None)
    if reviewed_topic_id and not reviewed:
        raise ValueError(f"人工复核topic不属于题目课程：{question.get('id')} -> {reviewed_topic_id}")
    if reviewed:
        return {
            "topic_id": reviewed["topic_id"],
            "topic_title": reviewed["title"],
            "chapter_id": reviewed["chapter_id"],
            "required_depth": reviewed["depth"],
            "topic_order": topics.index(reviewed),
        }
    if question.get("topic_source") == "manual":
        manual = next((topic for topic in topics if topic["topic_id"] == question.get("topic_id")), None)
        if manual:
            return {
                "topic_id": manual["topic_id"],
                "topic_title": manual["title"],
                "chapter_id": manual["chapter_id"],
                "required_depth": manual["depth"],
                "topic_order": topics.index(manual),
            }
    override_number = COURSE_TOPIC_OVERRIDES.get(subject, {}).get(str(question.get("id")))
    if override_number and override_number <= len(topics):
        best = topics[override_number - 1]
        return {
            "topic_id": best["topic_id"], "topic_title": best["title"],
            "chapter_id": best["chapter_id"], "required_depth": best["depth"],
            "topic_order": override_number - 1,
        }
    if subject in {"办公软件", "多媒体"}:
        stem = normalized_text(question.get("stem"))
        rules = (
            (
                (
                    (17, r"协作|版本冲突|链接对象|嵌入对象|兼容性检查|隐藏信息|交付检查"),
                    (16, r"跨组件|组合工具|综合任务|经营汇报"),
                    (15, r"动画|切换|放映|排练计时|演讲者视图"),
                    (14, r"母版|主题|版式|占位符"),
                    (13, r"图表|打印|保护|加密"),
                    (12, r"数据透视|分类汇总"),
                    (11, r"排序|筛选|数据验证|条件格式|冻结窗格"),
                    (10, r"vlookup|xlookup|countif|average|sum|if函数|函数|#n/a|#value|max|min"),
                    (9, r"相对引用|绝对引用|混合引用|$[a-z]"),
                    (8, r"工作簿|工作表|单元格|公式|填充序列|数据类型"),
                    (7, r"邮件合并|修订|批注|合并域"),
                    (6, r"题注|交叉引用|图片环绕|表格.*(?:行|列|单元格)|对象"),
                    (5, r"分节|页眉|页脚|页码|分页|分栏|页边距"),
                    (4, r"样式|自动目录|导航窗格|大纲"),
                    (2, r"自动恢复|备份|另存为|保存|恢复"),
                    (1, r"文件格式|扩展名|兼容|pdf|csv"),
                )
                if subject == "办公软件"
                else (
                    (16, r"交付检查|发布测试|版权|多终端"),
                    (15, r"需求分析|脚本|分镜|素材组织"),
                    (14, r"压缩比|节省率|格式选择"),
                    (13, r"无损|有损|冗余|压缩"),
                    (12, r"自适应|流媒体|缓冲|直播|点播|卡顿"),
                    (11, r"视频|编码器|容器|h.?264|mp4"),
                    (10, r"动画|关键帧|补间|时间轴|帧率"),
                    (9, r"midi|波形音频|wav|mp3|flac"),
                    (8, r"pcm|声音采集|音频容量|麦克风|声道"),
                    (7, r"图层|蒙版|透明|jpeg|jpg|png|gif|svg|psd"),
                    (6, r"rgb|cmyk|hsv|颜色模型|色域"),
                    (5, r"位图|矢量|像素|分辨率|重采样"),
                    (4, r"容量|码率|bit|byte"),
                    (3, r"采样|量化|奈奎斯特|数字化"),
                    (2, r"超文本|超媒体"),
                )
            )
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {
                    "topic_id": best["topic_id"], "topic_title": best["title"],
                    "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                    "topic_order": topic_number - 1,
                }
    if subject == "数据库":
        # 数据库题干中的“选择”“关系”等普通词很容易撞上关系代数。
        # 按独立解题任务使用题干规则，并让恢复、安全等窄主题优先匹配。
        override_number = DATABASE_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {
                "topic_id": best["topic_id"], "topic_title": best["title"],
                "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                "topic_order": override_number - 1,
            }
        stem = normalized_text(question.get("stem"))
        rules = (
            (18, r"grant|revoke|授予.*权限|收回.*权限|授权|审计|最小权限"),
            (17, r"\bwal\b|日志|后备副本|备份|恢复|\bredo\b|\bundo\b|检查点"),
            (16, r"并发|排它锁|共享锁|封锁|丢失更新|脏读|不可重复读|幻读|隔离级别|冲突优先图"),
            (15, r"\bacid\b|事务的.{0,3}(?:4|四)个特征|原子性|不可分割|全部成功|同一事务|逻辑工作单元|持久性|回滚|提交"),
            (14, r"无损|依赖保持|关系分解|伪元组"),
            (13, r"范式|规范化|\b1nf\b|\b2nf\b|\b3nf\b|\bbcnf\b|删除操作异常|部分依赖|传递依赖"),
            (12, r"属性闭包|闭包|函数依赖|候选键"),
            (11, r"需求分析|概念设计|逻辑设计|物理设计|数据库设计阶段|设计数据库"),
            (10, r"索引|b\+树|范围.*排序|文件组织|物理设计"),
            (6, r"\bcreate\b|\balter\b|\bdrop\b|\bdelete\b|\bupdate\b|\binsert\b|primarykey|foreignkey|notnull|\bunique\b|\bcheck\b|数据操纵功能"),
            (9, r"视图|\bview\b"),
            (8, r"leftjoin|innerjoin|\bjoin\b|子查询|\bexists\b|\bnotin\b|集合运算"),
            (7, r"\bselect\b|\bwhere\b|groupby|\bhaving\b|orderby|\bcount\b|\bavg\b|\bmax\b|\bmin\b|通配符|\bdistinct\b|sql语言的功能"),
            (3, r"e-r.*转|转换为.*关系模式|联系转换|联系表|外键.*(?:多端|n端)"),
            (2, r"e-r|er图|实体|一对多联系|1:n联系|m:n联系|概念模型"),
            (5, r"关系代数|投影运算|选择σ|五种基本运算|集合r与s的交|数据操纵即是建立在关系"),
            (4, r"主码|主键|候选|关键字|外码|外键|完整性|元组|二维表的.行|一行叫做|关系模式至少|关系模型"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {
                    "topic_id": best["topic_id"],
                    "topic_title": best["title"],
                    "chapter_id": best["chapter_id"],
                    "required_depth": best["depth"],
                    "topic_order": topic_number - 1,
                }
    if subject == "编程语言":
        override_number = PROGRAMMING_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {
                "topic_id": best["topic_id"], "topic_title": best["title"],
                "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                "topic_order": override_number - 1,
            }
        stem = normalized_text(question.get("stem"))
        rules = (
            (16, r"c与python|语言差异|两种语言"),
            (15, r"\btry\b|\bexcept\b|\bfinally\b|异常|withopen|valueerror|python.*文件"),
            (14, r"\bfopen\b|\bfclose\b|\bfeof\b|文件指针|文本文件|二进制文件|流式处理"),
            (13, r"\bstruct\b|结构体|->"),
            (12, r"指针|int\*|\*p|p\+\d|&x|地址|解引用|\bmalloc\b|\bfree\b"),
            (11, r"列表|元组|字典|集合|容器|切片|\bappend\b|\bsort\b|\blen\b|\brange\b.*切片"),
            (10, r"数组|字符数组|字符串|\bstrlen\b|\bsizeof\b"),
            (9, r"递归|作用域|全局变量|局部变量|调用栈|终止递归"),
            (8, r"函数|形参|实参|参数|返回值|\breturn\b|默认列表"),
            (7, r"\bfor\b|\bwhile\b|\brange\b|循环|\bbreak\b|\bcontinue\b"),
            (6, r"\bif\b|\belse\b|\belif\b|\bswitch\b|\bcase\b|条件分支|三目|\?"),
            (5, r"\bscanf\b|\bprintf\b|\binput\b|\bprint\b|键盘输入|输入语句|输出结果"),
            (4, r"运算符|表达式|短路|取模|整数除法|优先级|逗号表达式"),
            (3, r"变量|常量|数据类型|标识符|\bint\b|\bfloat\b|\bdouble\b|类型转换"),
            (2, r"编译|解释程序|语法错误|运行错误|逻辑错误|调试"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {
                    "topic_id": best["topic_id"], "topic_title": best["title"],
                    "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                    "topic_order": topic_number - 1,
                }
    if subject == "计算机组成原理":
        override_number = COMPUTER_ORGANIZATION_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {
                "topic_id": best["topic_id"], "topic_title": best["title"],
                "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                "topic_order": override_number - 1,
            }
        stem = normalized_text(question.get("stem"))
        rules = (
            (14, r"tlb|虚拟地址|物理地址|页表|页框|页号|缺页|mmu"),
            (13, r"\bdma\b|中断|程序查询|i/o|io方式|设备控制|统一编址|独立编址"),
            (12, r"总线|数据传输率|地址总线|数据总线|控制总线"),
            (11, r"流水线|数据相关|控制相关|结构冲突|数据转发|冒险"),
            (10, r"cache|命中率|失效率|平均访问|直接映射|全相联|组相联|写回|脏块"),
            (9, r"存储芯片|地址线|存储容量|按字节编址|按字编址|dram|sram|ram|rom|位信息|字扩展|位扩展"),
            (8, r"存储层次|局部性|寄存器.*cache|主存.*外存"),
            (7, r"寻址|有效地址|操作码|地址字段|risc|cisc|load/store"),
            (6, r"指令周期|取指|译码|\bpc\b|\bir\b|\bmar\b|\bmdr\b|\balu\b|运算器|控制器|除零异常"),
            (5, r"浮点|定点|阶码|尾数|规格化|对阶|ieee"),
            (4, r"原码|反码|补码|溢出|符号扩展|带符号"),
            (3, r"二进制|八进制|十六进制|数制|bcd|ascii|unicode|字符编码"),
            (2, r"\bcpi\b|cpu执行时间|主频|时钟频率|时钟周期|mips|性能"),
            (1, r"存储程序|冯·诺依曼|计算机系统|硬件系统|软件系统"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {
                    "topic_id": best["topic_id"], "topic_title": best["title"],
                    "chapter_id": best["chapter_id"], "required_depth": best["depth"],
                    "topic_order": topic_number - 1,
                }
    if subject == "信息安全":
        override_number = INFORMATION_SECURITY_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": override_number - 1}
        stem = normalized_text(question.get("stem"))
        rules = (
            (17, r"授权范围|合法目的|公开信息|知识产权|职业责任|合规|单位制度"),
            (16, r"个人信息|敏感个人信息|最小必要|去标识|匿名化|重新识别"),
            (15, r"事件响应|遏制|根除|复盘|保留证据|安全事件"),
            (14, r"\brpo\b|\brto\b|全量备份|增量备份|差异备份|3-2-1|备份恢复|raid"),
            (13, r"sql注入|xss|参数化查询|输出编码|主机加固|补丁|服务端校验"),
            (12, r"ddos|dos攻击|中间人|arp欺骗|dns欺骗|异常流量|误报|漏报"),
            (11, r"防火墙|\bids\b|\bips\b|\bdmz\b|\bvpn\b|\btls\b|网络分区"),
            (10, r"数字签名|证书|\bca\b|信任链|\bmac\b|哈希|摘要|防抵赖"),
            (9, r"对称加密|非对称加密|公钥|私钥|会话密钥|混合加密|密钥分发"),
            (8, r"访问控制|\bdac\b|\bmac\b|\brbac\b|\babac\b|角色|权限复核|授权"),
            (7, r"认证因素|多因素|\bmfa\b|会话|cookie|令牌|生物特征|账号恢复"),
            (6, r"社会工程|钓鱼|感染处置|隔离主机|勒索.*处置"),
            (5, r"病毒|蠕虫|木马|勒索软件|恶意代码|后门"),
            (4, r"口令|盐|慢散列|账号锁定|等级保护|等保|定级|测评"),
            (3, r"预防控制|检测控制|纠正控制|风险处置|风险规避|风险转移|风险接受"),
            (2, r"资产|威胁|脆弱性|攻击|风险|纵深防御|职责分离|最小权限"),
            (1, r"机密性|完整性|可用性|\bcia\b"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": topic_number - 1}
    if subject in {"计算机基础", "信息基础", "大数据"}:
        override_number = COMPUTER_FOUNDATION_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": override_number - 1}
        stem = normalized_text(question.get("stem"))
        rules = (
            (20, r"技术选型|组合技术|目标.*约束|时延.*隐私|可靠性.*风险|综合方案"),
            (19, r"信息系统|数字化转型|人员.*流程|系统建设"),
            (18, r"计算机发展|电子管|晶体管|集成电路|科学计算|数据处理|过程控制|辅助设计"),
            (17, r"智能合约|联盟链|公有链|私有链|普通数据库|多方共同"),
            (16, r"区块链|区块|共识|链式|上链|哈希.*篡改|数字签名.*区块"),
            (15, r"设备身份|固件|物联网安全|设备失联|安全状态|异常读数"),
            (14, r"物联网|传感器|执行器|网关|感知层|闭环控制"),
            (13, r"训练集|验证集|测试集|模型训练|模型推理|过拟合|生成式ai|幻觉"),
            (12, r"人工智能|机器学习|深度学习|监督学习|无监督学习|强化学习"),
            (11, r"数据挖掘|分类任务|回归|聚类|关联分析|异常检测|hadoop|hdfs|mapreduce|yarn|spark"),
            (10, r"大数据|\b4v\b|数据采集|数据清洗|缺失值|重复值|数据治理|数据仓库|流处理"),
            (9, r"公有云|私有云|混合云|边缘计算|云边协同|断网"),
            (8, r"云计算|\biaas\b|\bpaas\b|\bsaas\b|资源池|弹性|虚拟化"),
            (7, r"操作系统|任务管理器|资源管理器|\bipconfig\b|\bping\b|\bnslookup\b|系统软件|应用软件"),
            (6, r"文件|文件夹|目录|路径|扩展名|压缩包|格式转换"),
            (5, r"冯·诺依曼|存储程序|cpu|运算器|控制器|主存|外存|输入设备|输出设备|计算机硬件"),
            (4, r"ascii|unicode|utf-8|字符编码|像素|rgb|图像容量|采样|量化|声音编码"),
            (3, r"二进制|八进制|十六进制|数制转换|\bbit\b|\bbyte\b|容量计算"),
            (2, r"计算思维|问题分解|抽象|算法步骤|流程图|循环状态"),
            (1, r"数据.*信息|信息特征|信息载体|信息素养|可信|统计口径|时效性|共享性"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": topic_number - 1}
    if subject == "软件工程":
        override_number = SOFTWARE_ENGINEERING_TOPIC_OVERRIDES.get(str(question.get("id")))
        if override_number:
            best = topics[override_number - 1]
            return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": override_number - 1}
        stem = normalized_text(question.get("stem"))
        rules = (
            (19, r"追踪矩阵|需求到测试|持续改进|度量反馈|复盘"),
            (18, r"方法选择|组合工程方法|业务变化|按证据|演进式"),
            (17, r"风险管理|风险识别|风险应对|人员组织|团队沟通"),
            (16, r"关键路径|\bcpm\b|网络图|甘特图|工作量估算|项目估算|进度计划|成本估算"),
            (15, r"配置项|基线|版本控制|变更控制|配置管理|质量保证|质量审计"),
            (14, r"纠错性维护|适应性维护|完善性维护|预防性维护|软件维护|重构|再工程|逆向工程"),
            (13, r"单元测试|集成测试|系统测试|验收测试|桩模块|驱动模块|回归测试|调试"),
            (12, r"语句覆盖|分支覆盖|判定覆盖|条件覆盖|路径覆盖|环形复杂度|控制流图|白盒"),
            (11, r"等价类|边界值|决策表|因果图|黑盒"),
            (10, r"面向对象|\buml\b|类图|时序图|用例图|对象模型"),
            (9, r"内聚|耦合|信息隐藏|模块化|单一职责"),
            (8, r"总体设计|概要设计|详细设计|体系结构|接口设计|伪代码"),
            (7, r"\bdfd\b|数据流图|数据字典|数据流|数据存储|加工.*需求"),
            (6, r"需求获取|功能需求|非功能需求|需求规格|\bsrs\b|需求质量|需求变更|可验证需求"),
            (5, r"可行性|成本效益|投资回收期|技术可行|经济可行|操作可行"),
            (4, r"敏捷|scrum|迭代|持续集成|用户故事|短周期"),
            (3, r"瀑布|原型模型|增量模型|螺旋模型|统一过程|过程模型"),
            (2, r"生命周期|验证与确认|verification|validation|阶段评审"),
            (1, r"软件危机|软件工程|软件特点|工程化"),
        )
        for topic_number, pattern in rules:
            if re.search(pattern, stem, re.I):
                best = topics[topic_number - 1]
                return {"topic_id": best["topic_id"], "topic_title": best["title"], "chapter_id": best["chapter_id"], "required_depth": best["depth"], "topic_order": topic_number - 1}
    best = topics[0]
    if subject in {"算法与数据结构", "操作系统", "数据库", "编程语言", "计算机组成原理", "信息安全", "计算机基础", "信息基础", "大数据", "软件工程", "办公软件", "多媒体", "电路分析与电工技术", "模拟电子技术", "数字电子技术", "通信原理与高频电子线路", "信号与系统"}:
        core_text = question_text(question, include_options=False)
        stem_text = normalized_text(question.get("stem"))
        best_score = (0, 0, 0, 0, 0, 0, 0)
        for index, topic in enumerate(topics):
            matches = [keyword for keyword in topic.get("keywords", []) if normalized_text(keyword) in text]
            core_matches = [keyword for keyword in topic.get("keywords", []) if normalized_text(keyword) in core_text]
            stem_matches = [keyword for keyword in topic.get("keywords", []) if normalized_text(keyword) in stem_text]
            score = (
                max((len(normalized_text(keyword)) for keyword in stem_matches), default=0),
                len(stem_matches),
                max((len(normalized_text(keyword)) for keyword in core_matches), default=0),
                len(core_matches),
                max((len(normalized_text(keyword)) for keyword in matches), default=0),
                len(matches),
                -index,
            )
            if score > best_score:
                best = topic
                best_score = score
    else:
        best_score = (0, -1)
        for index, topic in enumerate(topics):
            matches = [keyword for keyword in topic.get("keywords", []) if normalized_text(keyword) in text]
            score = (max((len(normalized_text(keyword)) for keyword in matches), default=0), index)
            if score >= best_score:
                best = topic
                best_score = score
    if best_score[0] == 0:
        candidates = [topic for topic in topics if knowledge_point in topic.get("knowledge_points", [])]
        if candidates:
            best = candidates[0]
    return {
        "topic_id": best["topic_id"],
        "topic_title": best["title"],
        "chapter_id": best["chapter_id"],
        "required_depth": best["depth"],
        "topic_order": topics.index(best),
    }


def classify_knowledge_point(question: dict) -> str:
    subject = str(question.get("subject") or "")
    text = question_text(question)
    for label, keywords in SUBJECT_RULES.get(subject, ()):
        if any(keyword in text for keyword in keywords):
            return label
    return SUBJECT_DEFAULTS.get(subject, "综合基础")


def classify_ability(question: dict) -> str:
    subject = str(question.get("subject") or "")
    qtype = str(question.get("type") or "")
    # 学科名称只是分类，不是题目能力证据。若把“计算机组成原理”中的
    # “原理”用于匹配，会把普通名词识别题批量误标成机制解释题。
    text = normalized_text(question.get("stem"))

    if re.search(r"如图|图中|示意图|拓扑图|波形图|电路图|逻辑图|真值表|截图", text):
        return "读图排障"
    if re.search(r"排障|故障定位|无法访问|不能上网|ping通|nslookup|ipconfig|报错|异常外联|未授权登录", text):
        return "读图排障"
    if qtype == "简答" and subject == "数据库" and re.search(r"写(?:出)?\s*sql|sql查询|sql语句", text):
        return "SQL编写"
    if qtype == "简答" and re.search(r"编写(?:一段)?(?:程序|代码)|写一段.+代码|使用.+编程语言|用(?:python|c\+\+|c语言|java).{0,8}编写", text):
        return "代码编写"
    if subject == "编程语言" and (
        re.search(
            r"程序填空|程序段|以下程序|下列程序|代码|执行结果|运行结果|输出结果|输出为|"
            r"循环次数|变量.+值|表达式.+值|printf|scanf|print\s*\(|range\s*\(|len\s*\(",
            text,
        )
    ):
        return "程序阅读"
    if re.search(
        r"计算(?!机)|求出|求得|等于多少|容量约|理论容量|总电阻|等效电阻|容抗|感抗|阻抗|"
        r"码率|主机数|网络地址|广播地址|块大小|时间复杂度|命中率|吞吐率|可靠度|可信度|"
        r"十进制.+二进制|二进制.+十进制|帧数|采样率.+(?:秒|分钟)",
        text,
    ):
        return "直接计算"
    if re.search(r"过程|流程|步骤|顺序|阶段|生命周期|三次握手|四次挥手|dora|先后", text):
        return "过程描述"
    if re.search(r"区别|比较|相比|不同于|相同点|异同|辨析|二者|两者|前者.+后者", text):
        return "比较辨析"
    if re.search(
        r"某(?:单位|部门|学校|商场|系统|教师|用户|公司|网络|主机|电脑|服务器)|"
        r"场景|情境|案例|适合|宜采用|优先选择|应选择|最合理|较合理|用于.+应|需要.+(?:采用|使用|选择)",
        text,
    ):
        return "场景选型"
    if re.search(r"为什么|原因|机制|原理|如何实现|怎样实现|如何保证|保证.+的|依据|作用是|主要作用|说明理由", text):
        return "机制解释"
    if qtype == "简答":
        return "机制解释"
    return "概念识记"


ADVANCED_PATTERN = re.compile(
    r"vlsm|cidr地址块|分片偏移|拥塞窗口|银行家算法|安全序列|页面置换|缺页率|"
    r"bcnf|最小函数依赖|关系模式分解|关系代数表达式|递归算法|最短路径|最小生成树|"
    r"关键路径|圈复杂度|卡诺图化简|竞争冒险|状态方程|状态转换图|相量图|戴维宁等效|"
    r"诺顿等效|动态电路|拉普拉斯|傅里叶|误码率|香农公式|奈奎斯特|信道容量|"
    r"汇编|流水线冒险|cache地址映射|浮点运算|多级页表"
)


def classify_difficulty(question: dict, ability: str) -> str:
    text = question_text(question)
    qtype = str(question.get("type") or "")
    qid = str(question.get("id") or "")
    score = 0

    if ability in {"直接计算", "场景选型", "机制解释", "过程描述", "程序阅读", "代码编写", "SQL编写", "读图排障"}:
        score += 1
    if qtype in {"多选", "简答"}:
        score += 1
    if ADVANCED_PATTERN.search(text):
        score += 2
    if len(str(question.get("stem") or "")) >= 120:
        score += 1
    if qid.startswith(("uc-", "ue-")):
        score += 1

    if score >= 3:
        return "进阶"
    if score >= 1:
        return "应用"
    return "基础"


def derive_short_rubric(question: dict) -> list[dict]:
    explanation = str(question.get("explanation") or "")
    answer = str(question.get("answer") or "")
    match = re.search(r"(?:最低|最小)?得分点(?:为|包括)?[：:]?|评分点[：:]?", explanation)
    source = explanation[match.end():] if match else answer
    source = re.split(r"[。\n]", source, maxsplit=1)[0]
    parts = [part.strip(" ：:①②③④⑤⑥⑦⑧") for part in re.split(r"[、；;]", source)]
    if len([part for part in parts if len(part) >= 2]) < 2:
        parts = [part.strip(" ：:①②③④⑤⑥⑦⑧") for part in re.split(r"[；;。]", answer)]
    if len([part for part in parts if len(part) >= 2]) < 2:
        parts = [part.strip(" ：:") for part in re.split(r"(?:以及|和)", source)]
    if len([part for part in parts if len(part) >= 2]) < 2:
        parts = [part.strip(" ：:") for part in re.split(r"[，,]", answer)]
    criteria = []
    for part in parts:
        part = re.sub(r"^[（(]?[一二三四五六七八九十\d]+[)）.、]?", "", part).strip()
        if len(part) < 2 or part in criteria:
            continue
        criteria.append(part)
        if len(criteria) >= 8:
            break
    if not criteria:
        criteria = ["覆盖参考答案的核心结论"]
    return [{"criterion": criterion, "points": 1} for criterion in criteria]


def add_scoring_metadata(question: dict, metadata: dict[str, object]) -> dict[str, object]:
    combined = {**question, **metadata}
    if combined.get("type") == "简答" and (not combined.get("rubric") or combined.get("rubric_source") == "generated"):
        rubric = derive_short_rubric(combined)
        metadata.update({"rubric": rubric, "max_score": sum(item["points"] for item in rubric), "rubric_source": "generated"})
    elif combined.get("ability") == "直接计算" and combined.get("type") in {"填空", "简答"} and (not combined.get("rubric") or combined.get("rubric_source") == "generated"):
        rubric = [
            {"criterion": "写出适用公式或计算关系", "points": 1},
            {"criterion": "条件判断和单位处理正确", "points": 1},
            {"criterion": "代入与计算过程正确", "points": 1},
            {"criterion": "结果、单位或复杂度表达正确", "points": 1},
        ]
        metadata.update({"rubric": rubric, "max_score": 4, "rubric_source": "generated"})
    return metadata


def expected_metadata(question: dict) -> dict[str, object]:
    curated = NETWORK_QUESTIONS.get(question.get("id")) or GAP_QUESTIONS.get(question.get("id")) or MAINTAINED_QUESTIONS.get(question.get("id"))
    if curated:
        source = curated
        metadata = {key: source[key] for key in ("knowledge_point", "ability", "difficulty")}
        metadata.update(classify_course_topic({**question, **metadata}, metadata["knowledge_point"]))
        return add_scoring_metadata(question, metadata)
    ability = classify_ability(question)
    metadata = {
        "knowledge_point": classify_knowledge_point(question),
        "ability": ability,
        "difficulty": classify_difficulty(question, ability),
    }
    if question.get("subject") in COURSE_BY_SUBJECT:
        metadata.update(classify_course_topic({**question, **metadata}, metadata["knowledge_point"]))
    return add_scoring_metadata(question, metadata)


def enrich_questions(questions: list[dict]) -> tuple[list[dict], list[str]]:
    enriched: list[dict] = []
    changed_ids: list[str] = []
    for index, question in enumerate(questions, 1):
        if not isinstance(question, dict):
            raise ValueError(f"第{index}项不是题目对象")
        if str(question.get("id")) in REMOVED_QUESTION_IDS | REMOVED_LEGACY_COURSE_IDS | REMOVED_OLD_OFFICE_VERSION_IDS | REMOVED_OLD_MEDIA_PRODUCT_IDS | REMOVED_OFFICE_UI_TRIVIA_IDS:
            changed_ids.append(str(question.get("id")))
            continue
        source_question = dict(question)
        expected_subject = SUBJECT_OVERRIDES.get(str(question.get("id")))
        if expected_subject:
            source_question["subject"] = expected_subject
            source_question.pop("topic_source", None)
        metadata = expected_metadata(source_question)
        item = source_question
        item.update(metadata)
        removed_generated = False
        keeps_generated = item.get("type") == "简答" or (
            item.get("ability") == "直接计算" and item.get("type") == "填空"
        )
        if item.get("rubric_source") == "generated" and not keeps_generated:
            for field in ("rubric", "max_score", "rubric_source"):
                if field in item:
                    item.pop(field)
                    removed_generated = True
        if removed_generated or item.get("subject") != question.get("subject") or any(question.get(key) != value for key, value in metadata.items()):
            changed_ids.append(str(question.get("id") or f"#{index}"))
        enriched.append(item)
    return enriched, changed_ids


def print_distribution(questions: list[dict]) -> None:
    abilities = Counter(str(question.get("ability")) for question in questions)
    difficulties = Counter(str(question.get("difficulty")) for question in questions)
    knowledge = Counter(str(question.get("knowledge_point")) for question in questions)
    print("ability:", ", ".join(f"{key}={abilities[key]}" for key in sorted(ABILITY_VALUES)))
    print("difficulty:", ", ".join(f"{key}={difficulties[key]}" for key in ("基础", "应用", "进阶")))
    print(f"knowledge points: {len(knowledge)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="补充题库知识点、能力和难度元数据")
    parser.add_argument("--questions", type=Path, default=QUESTION_FILE)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查元数据是否已完整且与规则一致")
    mode.add_argument("--dry-run", action="store_true", help="只计算分布，不写文件")
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if not isinstance(questions, list):
        raise ValueError("题库根节点必须是JSON数组")
    enriched, changed_ids = enrich_questions(questions)
    print(f"questions: {len(enriched)}")
    print(f"metadata changes: {len(changed_ids)}")
    print_distribution(enriched)

    if args.check:
        if changed_ids:
            preview = ", ".join(changed_ids[:12])
            print(f"元数据缺失或过期：{preview}{' ...' if len(changed_ids) > 12 else ''}")
            return 1
        print("元数据检查通过")
        return 0
    if args.dry_run:
        return 0

    args.questions.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"元数据写入完成：{args.questions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
