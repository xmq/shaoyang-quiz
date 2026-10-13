"""Add original network exercises based on the reviewed national exam evidence."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "questions.json"
SOURCES = json.loads((ROOT / "network-exam-sources.json").read_text(encoding="utf-8"))
SOURCE_BY_ID = {source["id"]: source for source in SOURCES["sources"]}


def exercise(number, title, stem, options, answer, explanation, knowledge_point,
             ability, difficulty, source_id, source_items, question_type="单选",
             evidence_level="同考点变式", accepted_answers=None, rubric=None, topic_id=None):
    source = SOURCE_BY_ID[source_id]
    question = {
        "id": f"nw-national-{number:03d}",
        "source": "全国试题提炼",
        "type": question_type,
        "chapter": title,
        "stem": stem,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "subject": "计算机网络",
        "source_chapter": title,
        "source_url": source["url"],
        "source_title": source["title"],
        "adaptation_note": f"由{source_items}考查的知识任务重新命制；{source['kind']}，{source['status']}。",
        "source_id": source_id,
        "source_item": source_items,
        "evidence_level": evidence_level,
        "origin_verified": bool(source.get("verified_origin")),
        "answer_reviewed": True,
        "review_status": "approved",
        "version": 1,
        "knowledge_point": knowledge_point,
        "ability": ability,
        "difficulty": difficulty,
    }
    if accepted_answers:
        question["accepted_answers"] = accepted_answers
    if rubric:
        question["rubric"] = rubric
        question["max_score"] = sum(item["points"] for item in rubric)
    if topic_id:
        question["topic_id"] = topic_id
        question["topic_source"] = "manual"
    return question


NEW_QUESTIONS = [
    exercise(1, "物理层与容量", "某带宽为2 kHz的有噪声信道，线性信噪比为31。按香农公式计算，其理论容量是多少？",
             {"A": "4 kbit/s", "B": "8 kbit/s", "C": "10 kbit/s", "D": "20 kbit/s"}, "C",
             "C=B log₂(1+S/N)=2000×log₂32=10000 bit/s，即10 kbit/s。题目给的是线性比，无需再作分贝转换。",
             "物理层与传输介质", "直接计算", "应用", "nwnu-2015-a", "计算1"),
    exercise(2, "链路层CRC", "原始数据为1101，生成比特串为1011。发送前补零并进行模2除法后，应附加的3位CRC余数是什么？",
             {"A": "001", "B": "010", "C": "101", "D": "111"}, "A",
             "先补3个0得到1101000，以1011作模2除法得到余数001，因此发送1101001。CRC只检错，不负责自动纠错。",
             "数据链路与局域网", "直接计算", "应用", "ustc-2020-f", "计算2"),
    exercise(3, "IPv4子网", "主机地址10.77.23.5，子网掩码255.224.0.0。其网络地址是？",
             {"A": "10.64.0.0", "B": "10.77.0.0", "C": "10.96.0.0", "D": "10.77.23.0"}, "A",
             "255.224.0.0为/11，第二个八位组块大小32；77位于64—95，因此网络地址为10.64.0.0。",
             "IPv4与子网", "直接计算", "应用", "ustc-2020-f", "计算1"),
    exercise(4, "RIP路由更新", "R1当前经R2到目的网N的距离为2跳。R2随后报告自己到N为4跳，且没有更优邻居。R1应怎样处理？",
             {"A": "维持2跳", "B": "更新为经R2的5跳", "C": "更新为经R2的4跳", "D": "立即标记为16跳"}, "B",
             "当前下一跳R2的报告已变，R1经R2需要再加1跳，得到5跳。不能因新值变大而保留旧的2跳。",
             "路由与网络诊断", "过程描述", "进阶", "nwnu-2015-a", "综合1"),
    exercise(5, "最长前缀匹配", "路由器有10.0.0.0/8、10.4.0.0/16和10.4.7.0/24三条有效路由。目的地址10.4.7.20应匹配哪一条？",
             {"A": "10.0.0.0/8", "B": "10.4.0.0/16", "C": "10.4.7.0/24", "D": "三条随机选择"}, "C",
             "三条都覆盖目的地址，转发时选最具体的/24前缀。路由匹配不以出现顺序或跳数替代前缀长度。",
             "路由与网络诊断", "直接计算", "基础", "ustc-2020-f", "单选7"),
    exercise(6, "TCP窗口", "接收方通告的接收窗口rwnd为12 KB，发送方拥塞窗口cwnd为8 KB，已有3 KB数据在途未确认。忽略其他限制，此刻最多还能新增发送多少数据？",
             {"A": "3 KB", "B": "5 KB", "C": "8 KB", "D": "12 KB"}, "B",
             "在途数据上限为min(12,8)=8 KB；已占3 KB，因此尚可新增发送5 KB。",
             "TCP与UDP", "直接计算", "应用", "nwnu-2015-a", "单选10、综合2"),
    exercise(7, "以太网与无线接入", "比较传统共享半双工以太网与802.11无线接入的经典介质访问方式，正确的是？",
             {"A": "两者都主要依靠发送时冲突检测", "B": "以太网采用冲突检测，无线接入主要采用冲突避免", "C": "无线接入绝不发生碰撞", "D": "交换式全双工以太网必须运行CSMA/CD"}, "B",
             "共享半双工以太网用CSMA/CD；802.11主要用CSMA/CA。现代交换式全双工以太网没有共享碰撞域。",
             "数据链路与局域网", "比较辨析", "应用", "ustc-2020-f", "单选2、3及简答3"),
    exercise(8, "IPv4与IPv6地址", "下列关于IP版本的说法哪项正确？",
             {"A": "IPv4与IPv6地址均为32位", "B": "IPv6地址为128位，IPv6路由器不对数据报分片", "C": "IPv6仍使用IPv4的ARP广播解析地址", "D": "IPv6基本首部为128字节"}, "B",
             "IPv4地址32位，IPv6地址128位。IPv6由源主机处理分片，路由器不分片；IPv6基本首部为40字节。",
             "IPv4与子网", "比较辨析", "基础", "ustc-2020-f", "单选4、5"),
    exercise(9, "加密与签名", "某单位要让收件人验证文件确由指定发送者发出，且传输途中未被替换。哪种做法最适合？",
             {"A": "只发送文件及普通摘要", "B": "用发送者私钥签名，并验证公钥与其身份绑定", "C": "只对文件压缩", "D": "只用NAT转发文件"}, "B",
             "数字签名由私钥生成、公钥验证，结合可信的公钥身份绑定可检查来源与完整性。普通摘要可以一同被替换。",
             "计算机网络基础", "场景选型", "应用", "ustc-2020-f", "计算4", topic_id="net.crypto-signature"),
    exercise(10, "HTTP状态与排障", "浏览器收到HTTP 404响应。仅根据这个状态，最准确的判断是？",
             {"A": "本机一定没有网络连接", "B": "已经收到HTTP响应，但所请求的目标当前未找到", "C": "DNS服务器一定故障", "D": "目标网页文件一定过大"}, "B",
             "404表示响应方未找到请求的目标资源；响应可能来自源服务器或中间服务，不能直接判定本机物理断网或DNS故障。",
             "应用层协议", "比较辨析", "基础", "js-2019-copy", "多选73（仅作题型线索，非官方原卷）"),
    exercise(11, "信道容量与信噪比", "写出香农公式，说明公式中各参数的含义和单位，并说明信噪比以dB给出时怎样转换为线性功率比。",
             {}, "C=B log₂(1+S/N)。C为理论容量上限，单位bit/s；B为信道带宽，单位Hz；S为信号平均功率，N为噪声平均功率，二者使用相同功率单位；S/N为无量纲线性功率比。若信噪比为x dB，则S/N=10^(x/10)。",
             "香农公式用于有噪声、带宽受限信道的理论容量。作答时要同时写出公式、参数含义、单位和dB换算；不能把dB数值直接代入S/N。",
             "物理层与传输介质", "机制解释", "应用", "nwnu-2015-a", "计算1所考查的香农公式，并结合用户提供的简答题型重新命制", "简答", "用户反馈题型原创", rubric=[
                 {"criterion": "写出C=B log₂(1+S/N)", "points": 2},
                 {"criterion": "说明C、B的含义和单位", "points": 1},
                 {"criterion": "说明S、N及S/N的含义", "points": 1},
                 {"criterion": "写出dB转线性功率比的方法", "points": 1},
                 {"criterion": "说明C是理论容量上限", "points": 1},
             ]),
    exercise(12, "发送时延", "一个1500 B的数据帧通过100 Mbit/s链路发送。忽略其他开销，发送时延是多少微秒？只填写数字。",
             {}, "120", "计算题不会提示公式，需要先写出t=L/R。数据长度为1500×8=12000 bit，发送时延为12000/(100×10⁶)s=120 μs。",
             "物理层与传输介质", "直接计算", "应用", "nwnu-2016-b", "单选1涉及带宽与发送速率，重新命制无公式提示的填空计算", "填空", rubric=[
                 {"criterion": "默写t=L/R", "points": 1}, {"criterion": "把1500 B换成12000 bit", "points": 1},
                 {"criterion": "结果120 μs且单位正确", "points": 1},
             ]),
    exercise(13, "香农公式计算", "某有噪声信道带宽为3000 Hz，信噪比为30 dB。按香农公式计算理论容量，结果是多少kbit/s？可保留一位小数或取整数。",
             {}, "29.9", "先默写C=B log₂(1+S/N)。30 dB对应S/N=10³=1000，C=3000×log₂(1001)≈29901.7 bit/s，即约29.9 kbit/s，取整约30 kbit/s。",
             "物理层与传输介质", "直接计算", "进阶", "nwnu-2017-a", "计算1使用香农公式，重新设置数据并改为无公式提示的填空题", "填空", accepted_answers=["29.9", "29.90", "30"], rubric=[
                 {"criterion": "默写香农公式", "points": 1}, {"criterion": "把30 dB换为线性比1000", "points": 1},
                 {"criterion": "代入并完成对数计算", "points": 1}, {"criterion": "结果和kbit/s单位正确", "points": 1},
             ]),
    exercise(14, "IPv4子网", "一个传统IPv4子网采用/26前缀。网络地址和广播地址不分配给普通主机时，最多可分配多少个主机地址？只填写数字。",
             {}, "62", "主机位h=32-26=6，每块有2⁶=64个地址；传统普通子网扣除网络地址和广播地址，可用64-2=62个。",
             "IPv4与子网", "直接计算", "应用", "hbucm-2024-analysis", "综合题1考查IP地址设计和地址块计算，重新命制基础填空计算", "填空", rubric=[
                 {"criterion": "求出主机位h=6", "points": 1}, {"criterion": "求出每块2⁶=64个地址", "points": 1},
                 {"criterion": "扣除网络与广播地址得到62", "points": 1},
             ]),
    exercise(15, "TCP确认号", "某TCP报文段序号为1000，携带500 B数据，前序字节均已连续到达，且不含SYN和FIN。接收方应返回的确认号是多少？只填写数字。",
             {}, "1500", "确认号表示下一期待字节序号。前序连续到达且不含SYN/FIN时，ACK=SEQ+数据长度=1000+500=1500。",
             "TCP与UDP", "直接计算", "应用", "nwnu-2015-a", "运输层序号与窗口考查任务的基础计算变式", "填空", "课程补充", rubric=[
                 {"criterion": "写出ACK=SEQ+数据长度的适用条件", "points": 1},
                 {"criterion": "计算得到1500", "points": 1},
             ]),
    exercise(16, "停等利用率", "停等协议发送一帧需要1 ms，往返传播时间为9 ms，忽略确认发送时间、处理时间和丢失。链路利用率是多少百分比？只填写数字。",
             {}, "10", "简化模型U=T发送/(T发送+RTT)=1/(1+9)=0.1，即10%。题目若给单程传播时间，需要先换成往返时间。",
             "数据链路与局域网", "直接计算", "应用", "nwnu-2015-a", "单选4的可靠传输机制范围，重新命制无公式提示的利用率计算", "填空", "课程补充", rubric=[
                 {"criterion": "默写简化利用率公式", "points": 1}, {"criterion": "代入1 ms和9 ms", "points": 1},
                 {"criterion": "结果10%正确", "points": 1},
             ]),
    exercise(17, "TCP与UDP", "比较TCP与UDP在连接方式、可靠性、数据边界和典型适用场景上的区别。",
             {}, "TCP面向连接，提供可靠、有序的字节流，不保留应用消息边界，适合文件传输、网页和交易等强调可靠性的场景。UDP无连接，尽最大努力交付，保留数据报边界，首部开销较小，适合实时通信、简单查询或由应用自行实现可靠性的场景。",
             "作答需要覆盖连接、可靠性、数据组织和应用场景四个维度。TCP可靠不等于业务恰好执行一次；UDP也可以由应用增加确认与重传。",
             "TCP与UDP", "比较辨析", "应用", "nwnu-2013-b", "简答2涉及TCP可靠传输，扩展为常见协议比较简答", "简答", rubric=[
                 {"criterion": "连接方式", "points": 1}, {"criterion": "可靠性与顺序", "points": 1},
                 {"criterion": "字节流与数据报边界", "points": 1}, {"criterion": "适用场景", "points": 1},
             ]),
    exercise(18, "ARP与逐跳交付", "说明主机向同一子网和不同子网的目标发送IPv4数据时，ARP查询对象和首跳帧目的MAC地址有什么不同。",
             {}, "目标与本机同网时，主机用ARP查询目标主机的MAC，首跳帧目的MAC为目标主机MAC。目标在异网时，主机用ARP查询默认网关的MAC，首跳帧目的MAC为网关MAC，IP目的地址仍是远端目标地址。路由器转发时会重新封装下一跳链路帧。",
             "关键是先用IP地址和掩码判断是否同网。ARP只在本地广播域解析下一跳MAC，不会跨路由器查询远端主机MAC。",
             "IPv4与子网", "过程描述", "应用", "hbucm-2024-analysis", "计算题明确考查ARP请求报文和目的MAC，结合逐跳转发重新命制简答", "简答", rubric=[
                 {"criterion": "先判断是否同网", "points": 1}, {"criterion": "同网ARP对象与目的MAC", "points": 1},
                 {"criterion": "异网ARP对象与目的MAC", "points": 1}, {"criterion": "IP目的地址保持远端目标", "points": 1},
                 {"criterion": "说明逐跳重新封装", "points": 1},
             ]),
    exercise(19, "DNS与DHCP", "分别说明DNS和DHCP的主要作用，并简述主机不能通过域名访问网站、或获得169.254.x.x地址时的优先排查方向。",
             {}, "DNS负责名称解析，把域名对应到IP等记录；DHCP为主机分配IP地址、掩码、默认网关和DNS服务器等配置。能访问IP但不能访问域名时优先检查DNS配置与解析；获得169.254.x.x地址时通常说明未取得DHCP租约，应先检查本地链路、DHCP服务和中继。",
             "简答要把服务职责和故障现象对应起来。DNS故障不会直接把主机地址改成169.254网段，DHCP和DNS不能混为一种服务。",
             "DNS与DHCP", "过程描述", "应用", "nwnu-2016-b", "填空4和简答3涉及DHCP、ARP及DNS层次，重新命制职责与排障简答", "简答", rubric=[
                 {"criterion": "说明DNS作用", "points": 1}, {"criterion": "说明DHCP作用", "points": 1},
                 {"criterion": "域名异常的排查方向", "points": 1}, {"criterion": "169.254地址的排查方向", "points": 1},
             ]),
    exercise(20, "流量与拥塞控制", "比较TCP流量控制和拥塞控制的保护对象、主要依据和作用。",
             {}, "流量控制保护接收端，主要依据接收方通告的接收窗口，防止发送速度超过接收缓存能力。拥塞控制保护网络，依据拥塞窗口以及丢包、确认或显式拥塞信号调整发送量，避免向网络注入过多数据。实际可发送的在途数据受rwnd和cwnd较小者限制。",
             "需要明确两者保护对象不同：一个面向接收端能力，一个面向网络承载状态。接收窗口很大不代表网络不会拥塞。",
             "TCP与UDP", "比较辨析", "应用", "nwnu-2016-b", "简答2涉及慢开始、拥塞避免、快速重传和恢复，重新命制基础比较简答", "简答", rubric=[
                 {"criterion": "流量控制保护对象", "points": 1}, {"criterion": "流量控制主要依据", "points": 1},
                 {"criterion": "拥塞控制保护对象", "points": 1}, {"criterion": "拥塞控制主要依据", "points": 1},
             ]),
    exercise(21, "网络安全设施", "简述防火墙、IDS和IPS的主要作用，并说明它们为什么不能单独保证整个信息系统安全。",
             {}, "防火墙按规则允许或拒绝网络流量；IDS监测可疑活动并告警；IPS在检测基础上可主动阻断。它们主要处理网络流量风险，仍需与身份认证、权限控制、补丁、终端防护、日志监控和备份恢复等措施配合。",
             "简答先分别说明三种设施，再写安全边界。设备部署并不能自动解决弱口令、漏洞、内部越权和数据恢复等问题。",
             "计算机网络基础", "机制解释", "应用", "hbucm-2024-analysis", "简答题明确涉及网络安全威胁，重新命制设施作用与边界简答", "简答", "课程补充", rubric=[
                 {"criterion": "防火墙作用", "points": 1}, {"criterion": "IDS作用", "points": 1},
                 {"criterion": "IPS作用", "points": 1}, {"criterion": "说明单一设备的安全边界", "points": 1},
             ]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="核对新增题与来源定义是否同步")
    args = parser.parse_args()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.check:
        actual = {question["id"]: question for question in questions if question["id"].startswith("nw-national-")}
        expected = {question["id"]: question for question in NEW_QUESTIONS}
        synchronized = set(actual) == set(expected) and all(
            all(actual[qid].get(key) == value for key, value in definition.items())
            for qid, definition in expected.items()
        )
        if not synchronized:
            raise SystemExit("全国试题提炼练习与来源定义不同步")
        print(f"全国试题提炼练习已同步：{len(expected)}题")
        return
    before = len(questions)
    questions = [question for question in questions if not str(question.get("id") or "").startswith("nw-national-")]
    questions.extend(NEW_QUESTIONS)
    QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"同步{len(NEW_QUESTIONS)}题；题库{before}→{len(questions)}题")


if __name__ == "__main__":
    main()
