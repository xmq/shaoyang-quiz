"""Course-topic study priorities and suitable exam forms.

The forms combine stable abilities used by public-institution professional
exams, university finals and postgraduate subject exams. Complex questions are
split into smaller explanation, calculation and application tasks so that a
learner can master one step at a time.
"""

from topic_study_tasks import STUDY_TASKS

OBJECTIVE = "客观辨析"
SHORT_ANSWER = "简答说明"
CALCULATION = "直接计算"
APPLICATION = "综合应用"
CODE = "代码/语句"


KEY_TOPICS = set("""
office.t02 office.t03 office.t04 office.t05
multimedia.t02 multimedia.t03 multimedia.t04 multimedia.t05 multimedia.t06
operating-system.t03 operating-system.t04 operating-system.t05 operating-system.t06
database.t02 database.t03 database.t04 database.t05 database.t07 database.t08
data-structures.t01 data-structures.t02 data-structures.t03 data-structures.t04
data-structures.t05 data-structures.t06 data-structures.t07
programming.t02 programming.t03 programming.t05 programming.t06 programming.t07
programming.t08 programming.t09
computer-organization.t02 computer-organization.t03
computer-organization.t04 computer-organization.t05 computer-organization.t06
net.performance net.layers-addresses net.protocol-service net.channel-capacity
net.frames-switching net.subnet-routing net.arp-forwarding net.routing
net.ip-versions net.tcp-udp net.tcp-connection net.flow-congestion
net.app-protocols net.http net.dns-dhcp net.troubleshooting
circuit.t01 circuit.t02 circuit.t03 circuit.t05 circuit.t07
analog-electronics.t02 analog-electronics.t03 analog-electronics.t05 analog-electronics.t06
digital-electronics.t01 digital-electronics.t03
digital-electronics.t04 digital-electronics.t05 digital-electronics.t06
digital-electronics.t07
communication.t01 communication.t02 communication.t03 communication.t06 communication.t08
signals-systems.t01 signals-systems.t02 signals-systems.t03 signals-systems.t04
signals-systems.t05 signals-systems.t06
software-engineering.t02 software-engineering.t03 software-engineering.t04
software-engineering.t05 software-engineering.t06 software-engineering.t07
information-security.t01 information-security.t03
information-security.t04 information-security.t05 information-security.t06
information-security.t07
""".split())


SUPPLEMENT_TOPICS = set("""
computer-foundations.t04 computer-foundations.t05 computer-foundations.t06
computer-foundations.t07 computer-foundations.t08 computer-foundations.t10
""".split())


SHORT_ANSWER_TOPICS = set("""
office.t01 office.t02 office.t03 office.t06 office.t07
computer-foundations.t01 computer-foundations.t02 computer-foundations.t03
computer-foundations.t04 computer-foundations.t05 computer-foundations.t06
computer-foundations.t07 computer-foundations.t08 computer-foundations.t09 computer-foundations.t10
multimedia.t01 multimedia.t02 multimedia.t05 multimedia.t06 multimedia.t07
operating-system.t01 operating-system.t02 operating-system.t03 operating-system.t04
operating-system.t06 operating-system.t07 operating-system.t08
database.t01 database.t02 database.t03 database.t06 database.t07 database.t08 database.t09
data-structures.t01 data-structures.t02 data-structures.t03 data-structures.t04
data-structures.t05 data-structures.t06 data-structures.t07 data-structures.t08
programming.t01 programming.t02 programming.t05 programming.t07 programming.t08
programming.t09 programming.t10 programming.t11
computer-organization.t01 computer-organization.t03 computer-organization.t04
computer-organization.t05 computer-organization.t06 computer-organization.t07
net.overview net.performance net.switching net.layers-addresses net.protocol-service
net.media net.symbol-multiplexing net.channel-capacity net.frames-switching net.crc
net.arq-window net.ethernet-wifi net.subnet-routing net.arp-forwarding net.routing
net.ip-versions net.rip-update net.tcp-udp net.tcp-connection net.flow-congestion
net.app-protocols net.http net.dns-dhcp net.troubleshooting net.security-boundary
net.crypto-signature net.streaming-qos net.wireless-mobile
circuit.t01 circuit.t03 circuit.t04 circuit.t05 circuit.t06 circuit.t08 circuit.t09
analog-electronics.t01 analog-electronics.t02 analog-electronics.t03
analog-electronics.t04 analog-electronics.t05 analog-electronics.t06
analog-electronics.t07 analog-electronics.t08
digital-electronics.t01 digital-electronics.t02 digital-electronics.t03
digital-electronics.t04 digital-electronics.t05 digital-electronics.t06
digital-electronics.t07
communication.t01 communication.t02 communication.t03 communication.t04
communication.t05 communication.t06 communication.t07 communication.t08 communication.t09
signals-systems.t01 signals-systems.t02 signals-systems.t03 signals-systems.t04
signals-systems.t05 signals-systems.t06 signals-systems.t07
software-engineering.t01 software-engineering.t02 software-engineering.t03
software-engineering.t04 software-engineering.t05 software-engineering.t06
software-engineering.t07 software-engineering.t08
information-security.t01 information-security.t02 information-security.t03
information-security.t04 information-security.t05 information-security.t06
information-security.t07 information-security.t08
""".split())


CALCULATION_TOPICS = set("""
office.t04 office.t05
computer-foundations.t02
multimedia.t02 multimedia.t03 multimedia.t04 multimedia.t05
operating-system.t03 operating-system.t04 operating-system.t05 operating-system.t06
operating-system.t08
database.t02 database.t04 database.t05 database.t07 database.t08
data-structures.t01 data-structures.t02 data-structures.t03 data-structures.t04
data-structures.t05 data-structures.t06 data-structures.t07
computer-organization.t01 computer-organization.t02 computer-organization.t03
computer-organization.t04 computer-organization.t05 computer-organization.t06
computer-organization.t07
net.performance net.switching net.symbol-multiplexing net.channel-capacity
net.frames-switching net.crc net.arq-window net.subnet-routing net.arp-forwarding
net.routing net.ip-versions net.rip-update net.tcp-connection net.flow-congestion net.http net.streaming-qos
circuit.t01 circuit.t02 circuit.t03 circuit.t04 circuit.t05 circuit.t06 circuit.t07
analog-electronics.t02 analog-electronics.t03 analog-electronics.t04
analog-electronics.t05 analog-electronics.t06 analog-electronics.t07
digital-electronics.t01 digital-electronics.t02 digital-electronics.t03
digital-electronics.t04 digital-electronics.t05 digital-electronics.t06
digital-electronics.t07
communication.t02 communication.t03 communication.t04 communication.t06
communication.t08 communication.t09
signals-systems.t01 signals-systems.t02 signals-systems.t03 signals-systems.t04
signals-systems.t05 signals-systems.t06
""".split())


APPLICATION_TOPICS = set("""
office.t02 office.t03 office.t04 office.t05 office.t06 office.t07
computer-foundations.t03 computer-foundations.t07 computer-foundations.t10
multimedia.t02 multimedia.t03 multimedia.t04 multimedia.t05 multimedia.t07
operating-system.t03 operating-system.t04 operating-system.t05 operating-system.t06
operating-system.t07 operating-system.t08
database.t02 database.t03 database.t04 database.t05 database.t06 database.t07
database.t08 database.t09
data-structures.t01 data-structures.t02 data-structures.t03 data-structures.t04
data-structures.t05 data-structures.t06 data-structures.t07 data-structures.t08
programming.t03 programming.t04 programming.t05 programming.t06 programming.t07
programming.t08 programming.t09 programming.t10 programming.t11
computer-organization.t02 computer-organization.t03 computer-organization.t04
computer-organization.t05 computer-organization.t06 computer-organization.t07
net.performance net.switching net.layers-addresses net.symbol-multiplexing
net.channel-capacity net.frames-switching net.crc net.arq-window net.subnet-routing
net.arp-forwarding net.routing net.ip-versions net.rip-update net.tcp-connection
net.flow-congestion net.http net.dns-dhcp net.troubleshooting net.streaming-qos net.wireless-mobile
circuit.t01 circuit.t02 circuit.t03 circuit.t04 circuit.t05 circuit.t06 circuit.t07
circuit.t08 circuit.t09
analog-electronics.t02 analog-electronics.t03 analog-electronics.t04
analog-electronics.t05 analog-electronics.t06 analog-electronics.t07 analog-electronics.t08
digital-electronics.t01 digital-electronics.t02 digital-electronics.t03
digital-electronics.t04 digital-electronics.t05 digital-electronics.t06
digital-electronics.t07
communication.t02 communication.t03 communication.t04 communication.t05
communication.t06 communication.t07 communication.t08 communication.t09
signals-systems.t01 signals-systems.t02 signals-systems.t03 signals-systems.t04
signals-systems.t05 signals-systems.t06 signals-systems.t07
software-engineering.t02 software-engineering.t03 software-engineering.t04
software-engineering.t05 software-engineering.t06 software-engineering.t07
software-engineering.t08
information-security.t01 information-security.t02 information-security.t03
information-security.t04 information-security.t05 information-security.t06
information-security.t07 information-security.t08
""".split())


CODE_TOPICS = set("""
database.t04 database.t05 database.t08
data-structures.t02 data-structures.t03 data-structures.t04 data-structures.t05
data-structures.t06 data-structures.t07 data-structures.t08
programming.t03 programming.t04 programming.t05 programming.t06 programming.t07
programming.t08 programming.t09 programming.t10 programming.t11
net.tcp-connection
information-security.t07
""".split())

# 每门课程的知识点都是必学内容。这里仅区分复习顺序和最终掌握深度，
# 避免把整门课机械标成“优先练＋综合应用”。
def set_course_guidance(
    course_id: str,
    count: int,
    priority: tuple[int, ...] = (),
    short_answer: tuple[int, ...] = (),
    calculation: tuple[int, ...] = (),
    application: tuple[int, ...] = (),
    code: tuple[int, ...] = (),
    supplement: tuple[int, ...] = (),
) -> None:
    all_topics = {f"{course_id}.t{index:02d}" for index in range(1, count + 1)}
    for group in (KEY_TOPICS, SUPPLEMENT_TOPICS, SHORT_ANSWER_TOPICS, CALCULATION_TOPICS, APPLICATION_TOPICS, CODE_TOPICS):
        group.difference_update(all_topics)

    def selected(numbers: tuple[int, ...]) -> set[str]:
        return {f"{course_id}.t{index:02d}" for index in numbers}

    KEY_TOPICS.update(selected(priority))
    SUPPLEMENT_TOPICS.update(selected(supplement))
    SHORT_ANSWER_TOPICS.update(selected(short_answer))
    CALCULATION_TOPICS.update(selected(calculation))
    APPLICATION_TOPICS.update(selected(application))
    CODE_TOPICS.update(selected(code))


set_course_guidance(
    "office", 17,
    priority=(4, 5, 8, 9, 10, 11, 12, 14, 16),
    short_answer=(1, 2, 4, 5, 7, 10, 12, 14, 16, 17),
    calculation=(9, 10, 12),
    application=(4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17),
    supplement=(2, 3),
)
set_course_guidance(
    "computer-foundations", 20,
    priority=(2, 3, 5, 6, 7, 8, 10, 12, 14, 16),
    short_answer=(1, 2, 5, 7, 8, 10, 12, 14, 16, 19, 20),
    calculation=(3, 4),
    application=(2, 7, 8, 10, 12, 13, 14, 15, 16, 17, 20),
    supplement=(9, 11, 13, 15, 17, 18, 19),
)
set_course_guidance(
    "multimedia", 16,
    priority=(3, 4, 5, 8, 10, 11, 13, 14),
    short_answer=(1, 2, 3, 5, 8, 11, 12, 13, 15, 16),
    calculation=(3, 4, 8, 10, 11, 14),
    application=(5, 7, 11, 12, 15, 16),
    supplement=(2, 9, 15, 16),
)
set_course_guidance(
    "operating-system", 13,
    priority=(3, 4, 5, 6, 7, 8, 9, 10, 11, 13),
    short_answer=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    calculation=(5, 8, 9, 10, 13),
    application=(4, 5, 6, 7, 8, 9, 10, 11, 13),
    code=(6,),
    supplement=(),
)
set_course_guidance(
    "database", 18,
    priority=(2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 15, 16, 17),
    short_answer=tuple(range(1, 19)),
    calculation=(4, 5, 7, 8, 10, 12, 13, 14, 16, 17),
    application=(2, 3, 5, 8, 11, 12, 13, 14, 15, 16, 17, 18),
    code=(5, 6, 7, 8, 15, 16, 17, 18),
    supplement=(9, 11, 18),
)
set_course_guidance(
    "data-structures", 24,
    priority=(1, 3, 4, 5, 8, 9, 10, 12, 14, 15, 16, 18, 21, 23),
    short_answer=tuple(range(1, 25)),
    calculation=(1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 18, 19, 20, 21, 22, 23),
    application=(2, 3, 4, 5, 6, 14, 15, 16, 17, 24),
    code=(2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23),
    supplement=(7,),
)
set_course_guidance(
    "programming", 16,
    priority=(3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15),
    short_answer=(1, 2, 4, 8, 9, 10, 12, 14, 15, 16),
    calculation=(3, 4, 5, 6, 7, 10, 12),
    application=(6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
    code=tuple(range(1, 17)),
    supplement=(1, 2, 13, 16),
)
set_course_guidance(
    "computer-organization", 14,
    priority=(2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14),
    short_answer=(1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14),
    calculation=(2, 3, 4, 5, 7, 9, 10, 11, 12, 14),
    application=(2, 4, 5, 6, 7, 9, 10, 11, 13, 14),
    supplement=(8, 12),
)
set_course_guidance(
    "circuit", 12,
    priority=(2, 3, 4, 5, 6, 7, 10, 12),
    short_answer=tuple(range(1, 13)),
    calculation=(1, 2, 3, 4, 5, 6, 7, 9, 10, 11),
    application=(3, 4, 6, 7, 8, 10, 12),
    supplement=(9,),
)
set_course_guidance(
    "analog-electronics", 10,
    priority=(2, 3, 4, 5, 6, 7, 8, 10),
    short_answer=tuple(range(1, 11)),
    calculation=(2, 4, 5, 6, 7, 8, 9, 10),
    application=(4, 5, 6, 7, 8, 10),
    supplement=(1, 9),
)
set_course_guidance(
    "digital-electronics", 11,
    priority=(2, 3, 4, 5, 6, 7, 8, 11),
    short_answer=tuple(range(1, 12)),
    calculation=(1, 3, 4, 6, 7, 8, 9, 10, 11),
    application=(3, 4, 5, 6, 7, 8, 9),
    supplement=(1, 10),
)
set_course_guidance(
    "communication", 16,
    priority=(2, 3, 4, 5, 8, 9, 11, 14, 15),
    short_answer=tuple(range(1, 17)),
    calculation=(2, 3, 4, 5, 7, 8, 9, 11, 12, 14, 15, 16),
    application=(5, 6, 8, 9, 10, 12, 13, 14, 15, 16),
    supplement=(7, 13),
)
set_course_guidance(
    "signals-systems", 13,
    priority=(1, 2, 3, 5, 6, 8, 9, 11),
    short_answer=tuple(range(1, 14)),
    calculation=tuple(range(1, 13)),
    application=(3, 4, 5, 6, 8, 9, 10, 11, 12),
    supplement=(13,),
)
set_course_guidance(
    "software-engineering", 19,
    priority=(3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16),
    short_answer=tuple(range(1, 20)),
    calculation=(5, 12, 16),
    application=(3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19),
    supplement=(1, 2, 17),
)
set_course_guidance(
    "information-security", 17,
    priority=(1, 2, 4, 5, 7, 8, 9, 10, 11, 14),
    short_answer=tuple(range(1, 18)),
    application=(7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17),
    code=(13,),
    supplement=(3, 16, 17),
)

# Process and calculation tasks require early retrieval practice even when the
# bank currently contains few questions. Bank size never determines priority.
KEY_TOPICS.update({"net.symbol-multiplexing", "net.crc", "net.arq-window", "net.rip-update"})
KEY_TOPICS.update({"operating-system.t21", "programming.t22", "digital-electronics.t19"})
SHORT_ANSWER_TOPICS.update({"operating-system.t21", "programming.t22", "circuit.t15", "digital-electronics.t19", "office.t18", "computer-foundations.t24", "computer-foundations.t25", "software-engineering.t25"})
CALCULATION_TOPICS.update({"operating-system.t21", "circuit.t15", "digital-electronics.t19", "computer-foundations.t24"})
APPLICATION_TOPICS.update({"operating-system.t21", "programming.t22", "circuit.t15", "digital-electronics.t19", "office.t18", "computer-foundations.t25", "software-engineering.t25"})
CODE_TOPICS.add("programming.t22")

def guidance_for(topic_id: str) -> dict:
    practice_modes = [OBJECTIVE]
    mastery_steps = ["识别概念"]
    if topic_id in SHORT_ANSWER_TOPICS:
        practice_modes.append(SHORT_ANSWER)
        mastery_steps.append("完整说明")
    if topic_id in CALCULATION_TOPICS:
        practice_modes.append(CALCULATION)
        mastery_steps.append("直接计算")
    if topic_id in APPLICATION_TOPICS:
        practice_modes.append(APPLICATION)
        mastery_steps.append("分析应用")
    if topic_id in CODE_TOPICS:
        practice_modes.append(CODE)
        mastery_steps.append("读写语句")
    priority = "优先练" if topic_id in KEY_TOPICS else ("补充练" if topic_id in SUPPLEMENT_TOPICS else "正常练")
    target_depth = "综合应用" if topic_id in APPLICATION_TOPICS else (
        "直接应用" if topic_id in (SHORT_ANSWER_TOPICS | CALCULATION_TOPICS | CODE_TOPICS) else "识记理解"
    )
    result = {
        "core_status": "必学",
        "practice_priority": priority,
        "target_depth": target_depth,
        "mastery_steps": mastery_steps,
        "practice_modes": practice_modes,
        "short_answer": topic_id in SHORT_ANSWER_TOPICS,
    }
    if topic_id in STUDY_TASKS:
        result["study_task"] = STUDY_TASKS[topic_id]
    return result


def validate_guidance(topic_ids: set[str]) -> list[str]:
    configured = KEY_TOPICS | SUPPLEMENT_TOPICS | SHORT_ANSWER_TOPICS | CALCULATION_TOPICS | APPLICATION_TOPICS | CODE_TOPICS | set(STUDY_TASKS)
    return sorted(configured - topic_ids)
