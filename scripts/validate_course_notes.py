"""Validate lecture entry structure and chapter-level exam guidance."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COURSE_INDEX = ROOT / "course-index.json"
EXPECTED_COURSE_COUNT = 15
MIN_COURSE_CHARS = 3800
MIN_CHAPTER_CHARS = 180
MIN_PLAIN_EXPLANATIONS = 3
MAX_PLAIN_EXPLANATIONS = 8

H1_RE = re.compile(r"^#[ \t]+(.+?)\s*$")
H2_RE = re.compile(r"^##[ \t]+(.+?)\s*$")
MARKER_RE = re.compile(r"^<!--\s*exam:\s*([ABC])\s*\|\s*(.+?)\s*-->$")
BANNED_SECTION_RE = re.compile(
    r"(?:基础简答题|高频判断纠错|考前检查|考前自测|答题框架|答题模板|刷题)"
)
BANNED_COPY_RE = re.compile(
    r"(?:先答[：:]|显示答案|回忆卡|公开课程依据|教材依据|资料来源|考前冲刺|"
    r"答题|读题|题图|看波形题|判断时|常考|基础题|一步题|一步计算|基础读数|题干|遇到这种写法)"
)
BANNED_TITLE_RE = re.compile(r"(?:事业单位|招聘|招考|备考|冲刺)")
ALLOWED_QUESTION_TYPES = frozenset({
    "单选",
    "多选",
    "判断",
    "填空",
    "计算",
    "程序阅读",
    "状态判断",
    "场景题",
    "排障题",
    "简答",
})
REQUIRED_TOPICS = {
    "Office软件操作": (
        ("文字处理", r"Word|WPS文字"), ("电子表格", r"Excel|WPS表格"),
        ("演示文稿", r"PowerPoint|WPS演示"), ("单元格引用", r"单元格引用"),
        ("公式与函数", r"公式|函数"), ("排序与筛选", r"排序.*筛选|筛选.*排序"),
    ),
    "信息技术与教学论": (
        ("学习理论", r"学习理论"), ("教学设计", r"教学设计"),
        ("教学目标", r"教学目标"), ("课堂组织", r"课堂组织"),
        ("数字资源", r"数字资源"), ("教学评价", r"教学评价"),
    ),
    "多媒体技术": (
        ("采样量化编码", r"采样.*量化.*编码|抽样.*量化.*编码"),
        ("数字图像", r"数字图|位图|矢量图"), ("数字音频", r"数字音频|PCM"),
        ("动画与视频", r"动画.*视频|视频.*动画"), ("数据压缩", r"压缩"),
    ),
    "操作系统原理": (
        ("进程与线程", r"进程.*线程|线程.*进程"), ("处理机调度", r"调度"),
        ("同步与互斥", r"同步.*互斥|互斥.*同步"), ("死锁", r"死锁"),
        ("虚拟存储", r"虚拟存储|虚拟内存"), ("文件系统", r"文件系统"),
        ("设备管理", r"设备管理|I/O"),
    ),
    "数据库技术": (
        ("E-R模型", r"E-R|实体.*联系"), ("关系模型", r"关系模型"),
        ("SQL", r"SQL"), ("规范化", r"规范化|范式"), ("事务", r"事务"),
        ("并发隔离", r"隔离级别|并发控制"), ("恢复", r"恢复|UNDO|REDO"),
        ("索引", r"索引"),
    ),
    "数据结构与算法": (
        ("复杂度", r"时间复杂度|空间复杂度"), ("线性表", r"线性表"),
        ("栈与队列", r"栈.*队列|队列.*栈"), ("树", r"二叉树"),
        ("图", r"图的|图结构"), ("查找", r"查找"), ("排序", r"排序"),
    ),
    "编程语言": (
        ("C语言", r"C语言|```c"), ("Python", r"Python|```python"),
        ("变量与类型", r"变量.*类型|数据类型"), ("选择结构", r"选择结构|if.*else"),
        ("循环结构", r"循环结构|while|for"), ("函数", r"函数"),
        ("数组", r"数组"), ("指针", r"指针"), ("文件", r"文件"),
    ),
    "计算机组成原理": (
        ("冯诺依曼结构", r"冯.?诺依曼"), ("数据表示", r"补码"),
        ("CPU", r"CPU|中央处理器"), ("指令系统", r"指令"),
        ("存储层次", r"Cache|高速缓存"), ("虚拟存储", r"虚拟存储"),
        ("总线", r"总线"), ("输入输出", r"I/O|输入输出"),
    ),
    "计算机网络": (
        ("体系结构", r"OSI|TCP/IP"), ("物理层", r"物理层"),
        ("数据链路层", r"数据链路层"), ("IP与子网", r"IP.*子网|子网.*IP"),
        ("TCP与UDP", r"TCP.*UDP|UDP.*TCP"), ("应用层协议", r"DNS|HTTP"),
        ("网络排障", r"ping|tracert|traceroute"),
    ),
    "电路分析与电工技术": (
        ("基尔霍夫定律", r"KCL|KVL|基尔霍夫"), ("电路定理", r"戴维南|叠加定理"),
        ("电容电感", r"电容.*电感|电感.*电容"), ("正弦稳态", r"正弦|相量"),
        ("容抗", r"容抗"), ("一阶动态电路", r"一阶.*(?:RC|RL)|(?:RC|RL).*一阶"),
        ("三相电路", r"三相"),
    ),
    "模拟电子技术": (
        ("PN结与二极管", r"PN结.*二极管|二极管.*PN结"), ("BJT", r"BJT|三极管"),
        ("MOSFET", r"MOSFET|场效应"), ("静态工作点", r"静态工作点"),
        ("多级与差分放大", r"多级放大.*差分放大|差分放大.*多级放大"),
        ("频率响应", r"频率响应"), ("反馈", r"负反馈"),
        ("集成运算放大器", r"运算放大器|运放"), ("功率放大", r"功率放大"),
    ),
    "数字电子技术": (
        ("数制与码制", r"数制|码制|BCD"), ("逻辑代数", r"逻辑代数"),
        ("卡诺图", r"卡诺图"), ("组合逻辑", r"组合逻辑"),
        ("触发器", r"RS触发器|JK触发器"), ("时序逻辑", r"时序逻辑"),
        ("状态描述", r"状态表|状态图|状态方程"), ("计数器", r"计数器"),
        ("存储器", r"存储器|RAM|ROM"), ("模数与数模转换", r"ADC.*DAC|DAC.*ADC"),
    ),
    "通信原理与高频电子线路": (
        ("通信系统", r"信源.*信道.*信宿"), ("信道容量", r"香农"),
        ("抽样量化编码", r"抽样.*量化.*编码"), ("模拟调制", r"AM.*FM|FM.*AM"),
        ("数字调制", r"ASK|FSK|PSK|QAM"), ("基带与同步", r"基带.*同步|同步.*基带"),
        ("信道编码", r"信道编码"), ("高频接收", r"超外差|混频"),
        ("光纤通信", r"光纤"),
    ),
    "软件工程": (
        ("软件过程", r"软件过程|过程模型"), ("需求工程", r"需求工程"),
        ("软件设计", r"软件设计|概要设计"), ("软件测试", r"软件测试"),
        ("软件维护", r"(?:软件)?维护"), ("配置管理", r"配置管理"),
        ("项目管理", r"项目管理|WBS|甘特图"),
    ),
    "信息安全": (
        ("CIA目标", r"机密性.*完整性.*可用性"), ("风险管理", r"风险"),
        ("恶意代码", r"病毒.*蠕虫.*木马"), ("认证与访问控制", r"认证.*访问控制|访问控制.*认证"),
        ("密码技术", r"对称加密.*非对称|非对称.*对称加密"), ("网络安全", r"防火墙"),
        ("应用安全", r"SQL注入|XSS|CSRF"), ("备份恢复", r"备份.*恢复|恢复.*备份"),
        ("个人信息保护", r"个人信息"),
    ),
}


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def next_nonempty(lines: list[str], start: int) -> tuple[int, str] | None:
    for position in range(start, len(lines)):
        value = lines[position].strip()
        if value:
            return position, value
    return None


def main() -> int:
    configure_console()
    errors: list[str] = []
    levels: Counter[str] = Counter()
    marked_chapters = 0

    try:
        entries = json.loads(COURSE_INDEX.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法读取 {COURSE_INDEX.name}：{exc}", file=sys.stderr)
        return 1

    if not isinstance(entries, list) or len(entries) != EXPECTED_COURSE_COUNT:
        actual = len(entries) if isinstance(entries, list) else "非数组"
        errors.append(f"讲义索引应包含 {EXPECTED_COURSE_COUNT} 门课程，实际为 {actual}")
        entries = entries if isinstance(entries, list) else []

    for entry in entries:
        name = str(entry.get("name", "")).strip() if isinstance(entry, dict) else ""
        relative = str(entry.get("file", "")).strip() if isinstance(entry, dict) else ""
        path = ROOT / relative
        if not name or not relative or not path.is_file():
            errors.append(f"讲义索引项无效：{entry!r}")
            continue

        try:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}：无法读取讲义：{exc}")
            continue

        if len(source) < MIN_COURSE_CHARS:
            errors.append(f"{name}：讲义正文过短（{len(source)} 字符）")
        if source.count("```") % 2:
            errors.append(f"{name}：Markdown 代码围栏未成对闭合")
        explanation_count = source.count("**通俗理解：**")
        if explanation_count < MIN_PLAIN_EXPLANATIONS:
            errors.append(
                f"{name}：通俗解释不足（{explanation_count} 处，至少 {MIN_PLAIN_EXPLANATIONS} 处）"
            )
        if explanation_count > MAX_PLAIN_EXPLANATIONS:
            errors.append(
                f"{name}：通俗解释过多（{explanation_count} 处），疑似机械套用模板"
            )
        for topic, pattern in REQUIRED_TOPICS.get(name, ()):
            if not re.search(pattern, source, re.IGNORECASE | re.DOTALL):
                errors.append(f"{name}：缺少本科课程主干主题：{topic}")

        first = next_nonempty(lines, 0)
        if first is None or not H1_RE.match(first[1]):
            errors.append(f"{name}：第一行有效内容必须是一级标题")
            continue
        course_title = H1_RE.match(first[1]).group(1).strip()
        if BANNED_TITLE_RE.search(course_title):
            errors.append(f"{name}：课程标题含考试辅导措辞：{course_title}")
        for position, line in enumerate(lines, start=1):
            if BANNED_COPY_RE.search(line):
                errors.append(f"{name}：第 {position} 行含非讲义措辞：{line.strip()}")
        first_body = next_nonempty(lines, first[0] + 1)
        if first_body is None or not H2_RE.match(first_body[1]):
            errors.append(f"{name}：课程标题后应直接进入第一个知识章节")

        knowledge_chapters = 0
        chapter_positions = [
            position for position, line in enumerate(lines) if H2_RE.match(line.strip())
        ]
        for position, line in enumerate(lines):
            h2 = H2_RE.match(line.strip())
            if not h2:
                continue
            title = h2.group(1).strip()
            if BANNED_SECTION_RE.search(title):
                errors.append(f"{name} / {title}：禁止使用考试训练或通用模板章节")
                continue

            knowledge_chapters += 1
            chapter_number = chapter_positions.index(position)
            chapter_end = (
                chapter_positions[chapter_number + 1]
                if chapter_number + 1 < len(chapter_positions)
                else len(lines)
            )
            chapter_source = "\n".join(lines[position + 1:chapter_end])
            chapter_source = re.sub(r"<!--.*?-->|[#*`|\-]", "", chapter_source, flags=re.DOTALL)
            if len(re.sub(r"\s+", "", chapter_source)) < MIN_CHAPTER_CHARS:
                errors.append(f"{name} / {title}：章节内容过短，疑似只有提纲")
            following = next_nonempty(lines, position + 1)
            marker = MARKER_RE.match(following[1]) if following else None
            if not marker:
                errors.append(f"{name} / {title}：标题后缺少 exam 重要度与题型标记")
                continue

            question_types = [item.strip() for item in re.split(r"[、，,]", marker.group(2))]
            if any(not item for item in question_types):
                errors.append(f"{name} / {title}：题型标记中存在空项")
                continue
            unsupported = sorted(set(question_types) - ALLOWED_QUESTION_TYPES)
            if unsupported:
                errors.append(
                    f"{name} / {title}：存在未约定题型：{', '.join(unsupported)}"
                )
                continue
            if len(question_types) != len(set(question_types)):
                errors.append(f"{name} / {title}：题型标记存在重复项")
                continue
            levels[marker.group(1)] += 1
            marked_chapters += 1

        if knowledge_chapters == 0:
            errors.append(f"{name}：没有可学习的知识章节")

    if errors:
        print(f"讲义校验失败：共 {len(errors)} 个错误", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    level_text = "，".join(f"{level} 级 {levels[level]} 章" for level in "ABC")
    print(
        f"讲义校验通过：{len(entries)} 门课程，{marked_chapters} 个知识章节；{level_text}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
