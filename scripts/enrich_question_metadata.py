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


ROOT = Path(__file__).resolve().parents[1]
QUESTION_FILE = ROOT / "questions.json"

ABILITY_VALUES = frozenset({
    "概念识记",
    "比较辨析",
    "直接计算",
    "场景选型",
    "机制解释",
    "过程描述",
    "程序阅读",
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
        ("树与二叉树", ("二叉树", "树", "遍历", "哈夫曼", "叶子结点")),
        ("图结构与算法", ("图", "顶点", "边", "最短路径", "最小生成树", "深度优先", "广度优先")),
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
}

KNOWLEDGE_POINT_VALUES = frozenset(
    {label for rules in SUBJECT_RULES.values() for label, _ in rules}
    | set(SUBJECT_DEFAULTS.values())
    | {"综合基础"}
)


def normalized_text(*values: object) -> str:
    text = " ".join(str(value or "") for value in values)
    return unicodedata.normalize("NFKC", text).lower()


def question_text(question: dict, *, include_options: bool = True) -> str:
    values: list[object] = [
        question.get("subject"),
        question.get("chapter"),
        question.get("source_chapter"),
        question.get("stem"),
    ]
    if include_options:
        options = question.get("options")
        if isinstance(options, dict):
            values.extend(options.values())
    return normalized_text(*values)


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
    text = question_text(question, include_options=False)

    if re.search(r"如图|图中|示意图|拓扑图|波形图|电路图|逻辑图|真值表|截图", text):
        return "读图排障"
    if re.search(r"排障|故障定位|无法访问|不能上网|ping通|nslookup|ipconfig|报错|异常外联|未授权登录", text):
        return "读图排障"
    if subject == "编程语言" and (
        qtype == "填空"
        or re.search(
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

    if ability in {"直接计算", "场景选型", "机制解释", "过程描述", "程序阅读", "读图排障"}:
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


def expected_metadata(question: dict) -> dict[str, str]:
    ability = classify_ability(question)
    return {
        "knowledge_point": classify_knowledge_point(question),
        "ability": ability,
        "difficulty": classify_difficulty(question, ability),
    }


def enrich_questions(questions: list[dict]) -> tuple[list[dict], list[str]]:
    enriched: list[dict] = []
    changed_ids: list[str] = []
    for index, question in enumerate(questions, 1):
        if not isinstance(question, dict):
            raise ValueError(f"第{index}项不是题目对象")
        metadata = expected_metadata(question)
        if any(question.get(key) != value for key, value in metadata.items()):
            changed_ids.append(str(question.get("id") or f"#{index}"))
        item = dict(question)
        item.update(metadata)
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
