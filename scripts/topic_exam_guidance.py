"""Course-topic study priorities and suitable exam forms.

The forms combine stable abilities used by public-institution professional
exams, university finals and postgraduate subject exams. Complex questions are
split into smaller explanation, calculation and application tasks so that a
learner can master one step at a time.
"""

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

# 数据结构按独立解题任务拆成细粒度复习卡。题目仍可按章节练习，
# 重点页和错题回链则定位到具体结构或算法。
DATA_STRUCTURE_TOPICS = {f"data-structures.t{index:02d}" for index in range(1, 25)}
KEY_TOPICS.update(DATA_STRUCTURE_TOPICS)
SHORT_ANSWER_TOPICS.update(DATA_STRUCTURE_TOPICS)
APPLICATION_TOPICS.update(DATA_STRUCTURE_TOPICS)
CALCULATION_TOPICS.update({
    f"data-structures.t{index:02d}"
    for index in (1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 18, 19, 20, 21, 22, 23)
})
CODE_TOPICS.update({
    f"data-structures.t{index:02d}"
    for index in (2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23)
})

OPERATING_SYSTEM_TOPICS = {f"operating-system.t{index:02d}" for index in range(1, 14)}
KEY_TOPICS.update(OPERATING_SYSTEM_TOPICS)
SHORT_ANSWER_TOPICS.update(OPERATING_SYSTEM_TOPICS)
APPLICATION_TOPICS.update(OPERATING_SYSTEM_TOPICS)
CALCULATION_TOPICS.update({
    f"operating-system.t{index:02d}" for index in (5, 8, 9, 10, 13)
})
CODE_TOPICS.update({"operating-system.t06"})


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
    return {
        "core_status": "必学",
        "practice_priority": priority,
        "target_depth": target_depth,
        "mastery_steps": mastery_steps,
        "practice_modes": practice_modes,
        "short_answer": topic_id in SHORT_ANSWER_TOPICS,
    }


def validate_guidance(topic_ids: set[str]) -> list[str]:
    configured = KEY_TOPICS | SUPPLEMENT_TOPICS | SHORT_ANSWER_TOPICS | CALCULATION_TOPICS | APPLICATION_TOPICS | CODE_TOPICS
    return sorted(configured - topic_ids)
