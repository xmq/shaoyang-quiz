"""Build a data-driven, retrieval-based all-subject exam crash pack.

This is intentionally independent from color_notes/*.md.  The three-colour notes
are reference material; this pack is a last-day scoring workout generated from
question-bank frequencies plus hand-authored recall, comparison and answer frames.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT.parent / "冲刺资料"
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)


COURSES = [
    ("Office软件操作", "办公软件"),
    ("信息技术与教学论", "教学论"),
    ("多媒体技术", "多媒体"),
    ("操作系统原理", "操作系统"),
    ("数据库技术", "数据库"),
    ("数据结构与算法", "算法与数据结构"),
    ("编程语言", "编程语言"),
    ("计算机组成原理", "计算机组成原理"),
    ("计算机网络", "计算机网络"),
    ("电路分析与电工技术", "电路分析与电工技术"),
    ("模拟电子技术", "模拟电子技术"),
    ("数字电子技术", "数字电子技术"),
    ("通信原理与高频电子线路", "通信原理与高频电子线路"),
    ("信号与系统", None),
    ("软件工程", "软件工程"),
    ("信息安全", "信息安全"),
]


# Every entry is a scoring workout, not a restatement of the colour notes.
# routine entries use "name|method|meaning/boundary|micro example".
GUIDES = {
    "Office软件操作": {
        "recall": [
            "不看软件，口述 Word 长文档稳定排版链：样式→多级列表→分节→页眉页脚→目录→题注/交叉引用。",
            "在纸上写出相对、绝对、混合引用各一个例子，并说明公式向右、向下填充时谁变化。",
            "口述‘数据有效性—条件格式—排序筛选—分类汇总—透视表—图表’分别解决什么问题。",
            "给一份协作文档，列出修订、批注、接受/拒绝、版本备份的闭环操作。",
        ],
        "compare": [
            "分页符 vs 分节符|分页符只换页；分节符还能改变页边距、方向、页眉页脚和页码体系|题目出现‘本页横向/重新编号’优先分节",
            "VLOOKUP精确匹配 vs 近似匹配|FALSE/0要求完全相等；TRUE/1要求首列有序并做区间定位|学号、身份证号通常精确匹配",
            "嵌入对象 vs 链接对象|嵌入便携但文件大；链接可随源更新但路径失效会断链|跨电脑提交优先考虑嵌入或同时打包源文件",
        ],
        "routine": [
            "条件统计|COUNTIF/COUNTIFS按一个/多个条件计数|条件区域与统计区域尺寸必须一致|统计A班且成绩≥60：COUNTIFS(班级列,\"A班\",成绩列,\">=60\")",
            "条件求和|SUMIF/SUMIFS对满足条件的数值求和|SUMIFS先写求和区域，再写条件区域与条件|统计一组销售额：SUMIFS(金额列,组别列,\"一组\")",
            "查找防错|精确查找并用IFERROR处理未找到|查找键格式要一致，数字文本混用会失败|IFERROR(VLOOKUP(A2,表,3,0),\"未找到\")",
        ],
        "short": "设计‘月度数据汇总—趋势图—文字报告’流程。评分句：先清洗并用公式/透视表汇总，再选与任务匹配的图表并核验口径，最后在文字处理器中排版；嵌入便携、链接便于更新但依赖源路径。",
        "alerts": ["合并单元格会妨碍排序、筛选和透视分析", "目录不手敲页码，先用标题样式再自动生成", "公式结果异常先查括号、引用方式、数据类型和隐藏空格"],
    },
    "信息技术与教学论": {
        "recall": [
            "把‘理解筛选’改写为含行为、条件、标准的可测教学目标。",
            "分别为知识、操作技能、问题解决设计一条评价证据，并说明为什么能对应目标。",
            "口述导入—示范—分段练习—反馈—迁移任务—评价的课堂闭环。",
            "面对学生差异，写出支架、分层任务和形成性评价三项调整。",
        ],
        "compare": [
            "形成性评价 vs 总结性评价|前者在学习过程中诊断并改进；后者在阶段结束判断达成度|课堂练习反馈不是为了最终排名",
            "教师演示 vs 学生实操|演示降低初学负担并呈现过程；实操提供可观察的技能证据|会复述步骤不等于能完成操作",
            "教学目标 vs 教学活动|目标描述最终可观察表现；活动是达到目标的手段|‘观看视频’通常是活动而非学习结果",
        ],
        "routine": [
            "目标改写|对象+可观察行为+条件+达标标准|避免‘了解、掌握’等不可直接测量词|给定表格，3分钟内正确筛出两个条件且结果无误",
            "评价对齐|目标→任务→证据→反馈|考核层次不得低于目标层次|目标是排错，评价就应让学生实际诊断故障",
            "讲解降负荷|分段示范+即时练习+逐步撤除支架|材料越多不等于认知越深|演示两步后暂停，让学生复现并解释理由",
        ],
        "short": "批判‘连续20分钟演示软件、课后再练’。评分句：工作记忆容量有限，连续信息易造成认知超载；应分段演示、紧接操作、提供步骤支架和即时反馈，最后用新情境任务检验迁移。",
        "alerts": ["媒体新颖不等于教学有效，必须服务目标", "只考概念不能证明操作技能达成", "评价标准应在任务前明确且可观察"],
    },
    "多媒体技术": {
        "recall": [
            "从声音到文件口述：换能—调理—采样—量化—编码—压缩—封装。",
            "写出位图容量、音频容量、视频码率容量三类计算式并统一 bit/Byte。",
            "解释分辨率、色深、采样率、量化位数分别提高了什么、代价是什么。",
            "针对照片、图标、录音、流媒体各选择一种常用格式并说明理由。",
        ],
        "compare": [
            "位图 vs 矢量图|位图由像素构成，适合照片；矢量由几何描述，适合标志和线稿|位图放大会像素化，矢量复杂效果不一定占优",
            "有损 vs 无损压缩|有损舍弃感知次要信息、压缩率高；无损可完全还原|归档源文件、文字图表优先无损",
            "采样率 vs 量化位数|采样率决定时间分辨率和可表示最高频率；位数决定幅度级数和量化噪声|二者都会增加码率但作用不同",
        ],
        "routine": [
            "无压缩音频容量|采样率×量化位数×声道数×时间÷8|前三项得到bit/s，除8才是Byte|44.1kHz、16bit、双声道、10s≈1.764MB",
            "位图容量|宽×高×色深÷8|未计压缩、文件头和调色板|1920×1080×24bit≈5.93MiB",
            "压缩视频容量|码率×时间÷8|已有总码率时不能再乘分辨率与帧率|2Mbit/s×60s÷8=15MB（十进制）",
        ],
        "short": "解释声音数字化。评分句：麦克风将声波变为模拟电信号，经放大与抗混叠滤波后由ADC采样、量化、编码；采样使时间离散，量化使幅度离散，编码把量化结果表示为二进制。",
        "alerts": ["题目给出码率后不要再乘分辨率/帧率", "存储容量与通信速率的1000/1024口径以题干为准", "PNG无损不等于任何图都比JPEG小"],
    },
    "操作系统原理": {
        "recall": [
            "画出进程五状态并标出就绪↔运行、运行→阻塞、阻塞→就绪的触发原因。",
            "口述死锁四条件，并针对每个条件说一种破坏思路。",
            "解释分页、缺页、页面置换、抖动之间的因果链。",
            "用生产者—消费者说明互斥量和信号量分别保护什么。",
        ],
        "compare": [
            "程序 vs 进程 vs 线程|程序是静态指令；进程是资源分配/保护单位；线程是CPU调度执行单位|同进程线程共享地址空间但各有栈和寄存器现场",
            "互斥 vs 同步|互斥防止同时进入临界区；同步约束先后次序或资源数量|仅加锁不一定表达‘有数据才能消费’",
            "分页 vs 分段|分页固定大小、利于物理管理；分段按逻辑意义、长度可变|分页有内部碎片，分段易产生外部碎片",
        ],
        "routine": [
            "CPU调度判断|先画到达时间轴和就绪队列，再按算法选进程|周转时间=完成-到达，等待=周转-运行|抢占式算法每逢新进程到达都要重新比较",
            "页面置换|按访问串逐次维护页框并标记缺页|FIFO淘汰最早进入；LRU淘汰最久未用|先填空页框，满后才发生置换",
            "并发故障闭环|找共享数据→标临界区→选互斥/同步工具→检查粒度与死锁|原子性要覆盖完整业务不变量|库存检查和扣减应作为一个受控操作",
        ],
        "short": "两线程同时扣减库存为何出错？评分句：读—改—写不是原子操作，交错执行会产生竞态或丢失更新；应把检查和扣减作为临界区，用互斥锁/原子操作保护，并在业务层保证请求幂等。",
        "alerts": ["阻塞进程得到资源后先进入就绪态，不直接进入运行态", "死锁与饥饿不同：前者循环等待，后者长期得不到调度", "线程切换较轻但不是零开销"],
    },
    "数据库技术": {
        "recall": [
            "从自然语言需求写出SELECT—FROM—WHERE—GROUP BY—HAVING—ORDER BY的执行意图。",
            "解释实体完整性、参照完整性、用户定义完整性各约束什么。",
            "用一个订单表找部分依赖、传递依赖，并拆到3NF。",
            "口述事务ACID及脏读、不可重复读、幻读。",
        ],
        "compare": [
            "WHERE vs HAVING|WHERE在分组前筛行；HAVING在分组后筛组|聚合条件通常放HAVING",
            "主键 vs 外键 vs 唯一约束|主键唯一且非空标识本表行；外键引用他表键；唯一约束限制重复|外键可以重复，是否为空取决于约束",
            "B+树索引 vs 哈希索引|B+树支持等值、范围和排序；哈希擅长等值|索引加速读但增加空间与写维护成本",
        ],
        "routine": [
            "分组查询|先确定分组粒度，再确定聚合指标和组后条件|SELECT中的非聚合列通常必须在GROUP BY中|按班级统计平均分并筛平均≥80",
            "连接判断|先写关联键，再判断是否保留未匹配行|INNER只保留匹配；LEFT保留左表全部|查所有学生含无成绩者用LEFT JOIN",
            "并发更新|事务包裹读取与修改，使用锁或单条原子UPDATE|TCP可靠不等于事务隔离|UPDATE stock SET n=n-1 WHERE n>0",
        ],
        "short": "解释丢失更新并给出处理。评分句：两个事务读到相同旧值后分别写回，其中一次结果被覆盖；应使用合适隔离级别、行锁/乐观版本号，或把修改写成带条件的原子UPDATE。",
        "alerts": ["COUNT(*)计行，COUNT(列)忽略NULL", "NULL不能用=比较，应使用IS NULL", "规范化减少异常，但查询性能需求可能要求受控反规范化"],
    },
    "数据结构与算法": {
        "recall": [
            "看到‘先进先出、后进先出、优先级、快速键查找’分别立即联想到什么结构。",
            "口述DFS/BFS各用什么辅助结构、能解决什么问题。",
            "比较顺序、二分、散列、BST/B+树查找的前提和复杂度。",
            "写出常见排序最好/平均/最坏复杂度及稳定性，不求全背但要会排除。",
        ],
        "compare": [
            "栈 vs 队列 vs 优先队列|LIFO；FIFO；按优先级出队|紧急任务同优先级还需加入到达序保持FIFO",
            "BFS vs DFS|BFS逐层、无权图可求最短边数；DFS沿路深入、适合遍历/回溯|复杂度都通常为O(V+E)",
            "稳定排序 vs 不稳定排序|相等关键字相对次序是否保持|多字段分步排序时稳定性有实际意义",
        ],
        "routine": [
            "复杂度计数|只保留增长最快项并忽略常数|嵌套循环不能仅看层数，要看边界|Σ(i=1..n)i=n(n+1)/2，所以O(n²)",
            "二分查找|先确认有序，再维护闭区间或半开区间不变量|每次规模约减半，O(log n)|mid应避免边界更新不前进",
            "图存储选择|稠密/频繁查边选邻接矩阵；稀疏/遍历邻居选邻接表|矩阵空间O(V²)，表O(V+E)|社交网络通常稀疏，优先邻接表",
        ],
        "short": "订单按到达顺序处理且要按编号快速定位，如何选结构？评分句：顺序处理用队列维持FIFO，编号定位另建哈希表；新增同时入队并建索引，完成后出队并删索引，注意一致性和哈希冲突。",
        "alerts": ["堆只保证父子次序，不保证全局有序", "二分查找前提是可随机访问的有序序列", "哈希平均O(1)不等于最坏O(1)"],
    },
    "编程语言": {
        "recall": [
            "对一段分支循环代码，逐行写变量表、条件真假和输出，不凭感觉跳步。",
            "说明值传递、引用/对象共享、指针参数修改调用方数据的区别。",
            "口述数组越界、空指针、内存泄漏、悬空指针各自成因。",
            "写出文件打开—检查—读写—异常处理—关闭的完整链。",
        ],
        "compare": [
            "编译错误 vs 运行错误 vs 逻辑错误|分别在翻译、执行、结果语义阶段暴露|测试主要发现后两类，编译通过不代表正确",
            "C数组 vs Python列表|C数组元素类型和长度更固定、需管边界；列表动态且存对象引用|Python方便不代表没有索引越界",
            "浅拷贝 vs 深拷贝|浅拷贝共享嵌套对象；深拷贝递归复制|修改嵌套元素时差异最明显",
        ],
        "routine": [
            "代码跟踪|列出输入、变量初值、每轮变化、终止条件、输出|短路求值和自增位置要单独标记|循环题至少手算0次、1次和边界次数",
            "递归分析|写终止条件、规模缩小、返回组合|无终止或规模不缩小会无限递归|阶乘：n=0返回1，否则n×f(n-1)",
            "文件持久化|选择模式→检查打开→读写→处理失败→可靠关闭|w模式会截断旧内容|Python用with，C检查FILE*并fclose",
        ],
        "short": "怎样可靠分析分支循环题？评分句：先确定语言语义和输入类型，建立变量跟踪表，逐次判断条件与更新，检查0次/边界/终止情况，最后核对输出；C还要查整除、越界和指针，Python要查缩进、可变对象与类型。",
        "alerts": ["C整数相除会截断，除数不能为0", "赋值=与比较==不要混淆", "循环边界重点查<与<=造成的差一错误"],
    },
    "计算机组成原理": {
        "recall": [
            "按取指—译码—取数—执行—写回口述一条指令在CPU中的数据流。",
            "画存储层次并解释容量、速度、成本为什么逐级折中。",
            "写出中断全过程：请求—响应—保护现场—服务—恢复—返回。",
            "区分Cache未命中、TLB未命中、缺页三者查找对象和代价。",
        ],
        "compare": [
            "Cache vs TLB|Cache缓存主存数据块；TLB缓存页表项/地址转换|TLB未命中不必然缺页，可继续查页表",
            "中断I/O vs DMA|中断适合事件/中小传输，由CPU参与；DMA适合成块高速传输，只在启动/完成等时刻打扰CPU|DMA仍需CPU配置",
            "RISC vs CISC|RISC指令较规整、利于流水；CISC指令丰富、单指令功能复杂|现代处理器常融合两者思想",
        ],
        "routine": [
            "CPU时间|T=指令数IC×平均CPI÷时钟频率f|性能同时受程序、体系结构和频率影响|IC=10⁹,CPI=2,f=2GHz，则T=1s",
            "Cache平均访存|Tavg=命中时间+失效率×未命中代价|概率用小数且口径保持一致|1ns+2%×50ns=2ns",
            "补码运算|统一位宽→写补码→相加→舍弃最高进位→判断溢出|同号相加得异号才是有符号溢出|8位127+1得到10000000，发生溢出",
        ],
        "short": "为什么提高主频不一定使程序同比加速？评分句：CPU时间=IC×CPI/f；主频升高会减小周期，但指令数和CPI受程序、流水停顿、访存及架构影响，还受功耗散热约束，因此必须比较实际执行时间。",
        "alerts": ["命中率高不等于平均时间必然低，还看未命中代价", "流水线提高吞吐率，不等于单条指令延迟同比下降", "地址位数、容量单位和按字/按字节编址要先辨口径"],
    },
    "计算机网络": {
        "recall": [
            "从应用到物理层口述DNS查询后访问网页的封装、寻址和可靠传输过程。",
            "不看答案完成/24划4个等长子网，并写网络、主机范围、广播地址。",
            "比较TCP三次握手、可靠机制、流量控制和拥塞控制各解决什么问题。",
            "口述‘能ping IP不能访问域名’和‘同网段能通跨网段不通’的排错链。",
        ],
        "compare": [
            "TCP vs UDP|TCP面向连接、可靠字节流；UDP无连接、尽力而为、报文边界保留|实时性要求高不等于永远选UDP，还看业务容错",
            "交换机 vs 路由器|交换机主要按MAC在二层转发；路由器按IP跨网段选择路径|广播域通常由路由器划分",
            "DNS vs DHCP|DNS做名称到地址等解析；DHCP动态分配IP、掩码、网关、DNS等参数|能拿到IP不代表DNS一定可用",
        ],
        "routine": [
            "子网划分|借位数n满足子网数，主机位h满足2^h-2≥主机数|块大小=256-掩码末字节|/24划4个：借2位得/26，块长64，每网62主机",
            "端到端时延|发送时延=L/R；传播时延=d/v；总时延还含处理和排队|一个看包长/速率，一个看距离/传播速度|先统一bit、s、m单位",
            "故障定位|物理→本机配置→同网关→远端IP→DNS/端口→应用|每一步只验证一层假设|ping 8.8.8.8通而域名失败，优先查DNS",
        ],
        "short": "将192.168.10.0/24等分为4个子网。评分句：借2位得到/26，掩码255.255.255.192，块长64；网络地址为.0、.64、.128、.192，各有62个可用主机，广播分别为.63、.127、.191、.255。",
        "alerts": ["网络地址和广播地址通常不可分配给主机", "ping通只证明相关ICMP路径，不证明应用端口正常", "可靠传输是端到端语义，不由链路层单独保证"],
    },
    "电路分析与电工技术": {
        "recall": [
            "拿到电路先标参考方向，再写KCL/KVL；若结果为负，解释为真实方向相反。",
            "口述戴维南等效三步：开路电压、等效电阻、接回负载，并说明独立源置零规则。",
            "写出RC一阶响应的初值、终值、时间常数和一个τ比例。",
            "从现象到仪表选择，口述安全排障：断电确认—分段测量—定位—修复—复测。",
        ],
        "compare": [
            "节点电压法 vs 网孔电流法|前者以节点KCL为主，适合少节点；后者以网孔KVL为主，适合平面少网孔|含电流源常优先节点法",
            "有功P vs 无功Q vs 视在S|P做净功，Q往返交换能量，S反映设备容量；S²=P²+Q²|功率因数提高不等于负载有功功率凭空增加",
            "电压表 vs 电流表|电压表高内阻并联；电流表低内阻串联|电流挡并接电源可能短路",
        ],
        "routine": [
            "直流功率|P=UI=I²R=U²/R|后两式只直接适用于电阻，注意关联参考方向|10V加5Ω：I=2A，P=20W",
            "功率因数|单相P=UIcosφ，所以I=P/(Ucosφ)|P、U不变时提高cosφ可降电流与I²R损耗|补偿过度会变为容性，不是越多越好",
            "RC充电|uC(t)=U终+(U初-U终)e^(-t/RC)|τ=RC决定快慢，电容电压通常不能突变|由0充到10V，一个τ约6.32V",
        ],
        "short": "为什么提高功率因数能降低线损？评分句：在负载有功功率P和电压U不变时，I=P/(Ucosφ)；cosφ提高使电流减小，而线路损耗近似I²R，因此下降。补偿要适度且不会增加负载有功功率。",
        "alerts": ["受控源求等效电阻时不能随独立源一起置零", "电阻挡不能带电测量", "三相线/相电压、电流关系取决于星形或三角形连接"],
    },
    "模拟电子技术": {
        "recall": [
            "看到二极管先判断极性和导通条件，再决定用截止还是恒压降模型。",
            "用静态工作点解释BJT截止、放大、饱和及输出削顶。",
            "写出理想运放在线性负反馈下的虚短、虚断，并说明成立条件。",
            "口述负反馈对增益稳定、带宽、失真、输入/输出电阻的典型影响。",
        ],
        "compare": [
            "截止 vs 放大 vs 饱和|截止近似断开；放大区满足受控放大；饱和近似闭合|IC=βIB主要用于放大区",
            "反相 vs 同相运放|反相增益-Rf/Rin且输入电阻约Rin；同相增益1+Rf/Rg且输入电阻高|符号和接法必须同时判断",
            "稳压二极管 vs 普通二极管|稳压管利用规定反向击穿区；普通管多用正向导通/反向截止|稳压管必须限流并满足功耗",
        ],
        "routine": [
            "反相放大|Au=-Rf/Rin|负号表示反相，需线性负反馈且输出未饱和|Rf=100k,Rin=10k，增益-10",
            "同相放大|Au=1+Rf/Rg|输入加同相端，输出受电源轨与摆幅限制|Rf=90k,Rg=10k，增益10",
            "器件排障|先电源→静态点→输入→逐级输出→负载|万用表看直流、示波器看波形|单侧削顶先查静态点过高/过低而非直接换管",
        ],
        "short": "BJT三状态怎样判别及为何不能总用IC=βIB？评分句：截止时IC近零用于开关断；放大区用于线性放大且近似满足IC=βIB；饱和时管压降低用于开关闭，电流由外电路限制，β关系不再成立。",
        "alerts": ["虚短虚断只在线性负反馈且未饱和时使用", "耦合电容隔直通交但低频下容抗变大", "负反馈类型要按取样量和混合方式判断"],
    },
    "数字电子技术": {
        "recall": [
            "把逻辑表达式依次化简、列真值表、画门电路，并用另一种方式互相校验。",
            "区分组合逻辑和时序逻辑：输出是否依赖历史状态、是否含存储单元。",
            "写出D、JK触发器的下一状态关系，并解释建立/保持时间。",
            "口述ADC链：采样—保持—量化—编码；DAC则把数字量变为模拟量。",
        ],
        "compare": [
            "组合逻辑 vs 时序逻辑|组合输出只依赖当前输入；时序输出还依赖历史状态|锁存报警必须用时序存储",
            "同步计数器 vs 异步计数器|同步各触发器共用时钟、速度高；异步逐级触发、结构简单但延迟累积|高频和精确译码优先同步",
            "锁存器 vs 边沿触发器|锁存器在有效电平期间透明；触发器通常在边沿采样|时序图必须看电平还是边沿有效",
        ],
        "routine": [
            "逻辑化简|先用代数/卡诺图找最小项相邻合并，再保留必要项|卡诺图边缘相邻且分组为2的幂|别把无关项当固定0，合理利用可进一步化简",
            "ADC分辨率|量化级数2^n；理想步距约满量程/2^n|n为位数，端点口径以题干为准|0~5V、8位，步距约19.5mV",
            "PWM平均作用|占空比D=Ton/T，理想平均电压≈D·V|频率过低闪烁/脉动，过高增加开关损耗|12V、25%占空比，理想平均约3V",
        ],
        "short": "报警恢复后仍保持、按复位才熄灭，选什么逻辑？评分句：选时序逻辑并用触发器保存状态，因为输出不仅取决于当前传感器，还取决于过去是否报警；置位记录报警，复位清除状态。",
        "alerts": ["卡诺图按格雷码排列，不是自然二进制顺序", "竞争冒险来自传播延迟，代数等价不保证瞬态无毛刺", "ADC位数提高不能自动消除前端噪声或参考误差"],
    },
    "通信原理与高频电子线路": {
        "recall": [
            "画通信系统方框图并逐块解释信源编码、信道编码、调制、信道、解调、译码。",
            "写出奈奎斯特抽样条件和香农容量式，逐个解释变量及适用边界。",
            "比较AM、FM以及ASK/FSK/PSK的信息承载量、带宽和抗扰特点。",
            "口述载波同步、位同步、帧同步各恢复什么参考。",
        ],
        "compare": [
            "信源编码 vs 信道编码|前者去冗余降码率；后者加受控冗余以检错纠错|压缩与纠错目标相反但可串联使用",
            "AM vs FM|AM信息在幅度包络，设备较简；FM信息在频率变化，抗幅度噪声较强但带宽常更大|弱信号下FM也会恶化",
            "CRC vs ARQ|CRC主要检错；ARQ依靠确认、超时和重传恢复|CRC通常不能自行纠错，ARQ引入时延",
        ],
        "routine": [
            "抽样定理|fs≥2fmax|fs为采样频率，fmax为带限信号最高频率；工程需留过渡带|最高4kHz语音理论至少8kHz采样",
            "香农容量|C=B log2(1+S/N)|C bit/s，B Hz，S/N为线性功率比|SNR=30dB时先换成10^(30/10)=1000",
            "PCM码率|Rb=fs×n×声道数|n为每样本量化位数，未含信道编码开销|8kHz×8bit×1=64kbit/s",
        ],
        "short": "为何一般FM比AM抗幅度干扰强？评分句：AM的信息直接承载在幅度包络，幅度噪声会污染信息；FM的信息承载在频率变化，可在解调前限幅。代价是通常占更宽带宽、设备更复杂，弱信号下也会恶化。",
        "alerts": ["dB不能直接代入香农式，要先转线性比", "抽样率达标不代表无需抗混叠滤波", "带宽、信噪比和容量有上限关系，编码不能突破香农极限"],
    },
    "信号与系统": {
        "recall": [
            "对任一系统逐项检查线性、时不变、因果、稳定，写出验证或反例。",
            "画单位冲激、单位阶跃并说明二者的微分/积分关系。",
            "口述卷积的翻转—平移—相乘—积分/求和四步。",
            "写出傅里叶、拉普拉斯、Z变换分别主要解决什么问题及收敛域意义。",
        ],
        "compare": [
            "因果性 vs 稳定性|因果要求输出不依赖未来输入；BIBO稳定要求有界输入产生有界输出|二者互不等价",
            "连续卷积 vs 离散卷积|前者积分，后者求和；都由输入与冲激响应决定LTI输出|先判断重叠区间再算",
            "频率响应 vs 系统函数|频率响应描述稳态正弦响应；系统函数还结合复频域和收敛域表征结构|H(jω)存在需虚轴位于ROC",
        ],
        "routine": [
            "LTI输出|y=x*h；连续为∫x(τ)h(t-τ)dτ，离散为Σx[k]h[n-k]|h是单位冲激响应|两个宽度1矩形卷积得到底宽2的三角形",
            "BIBO稳定|连续∫&#124;h(t)&#124;dt<∞；离散Σ&#124;h[n]&#124;<∞|这是LTI系统判据|h(t)=e^-t u(t)绝对可积，稳定",
            "正弦响应|输入e^(jωt)，稳态输出H(jω)e^(jωt)|幅值乘&#124;H&#124;、相位加∠H|低通对高频通常衰减并产生相移",
        ],
        "short": "如何判断LTI系统因果稳定？评分句：因果要求连续系统h(t)=0(t<0)或离散系统h[n]=0(n<0)；BIBO稳定要求冲激响应绝对可积/绝对可和。必须分别检查，不能把因果当稳定。",
        "alerts": ["卷积中必须先翻转再平移", "系统函数相同而ROC不同，系统性质可能不同", "频域相乘对应时域卷积，别把两边运算同时写反"],
    },
    "软件工程": {
        "recall": [
            "把一句模糊需求改成可测条件、指标、阈值，并写验收证据。",
            "口述需求获取—分析—规格说明—确认—变更追踪闭环。",
            "比较单元、集成、系统、验收测试的对象和责任边界。",
            "为紧急修复写出授权—修改—测试—回退—发布验证—留痕最小流程。",
        ],
        "compare": [
            "验证 vs 确认|验证关注‘是否按规格正确构建’；确认关注‘是否构建了用户需要的产品’|评审和测试都可提供证据但问题不同",
            "黑盒 vs 白盒测试|黑盒依据外部规格设计输入输出；白盒依据内部结构覆盖路径/分支|两者互补而非替代",
            "高内聚 vs 低耦合|模块内部职责集中；模块之间依赖少且清晰|目的在于限制变更传播并提高可维护性",
        ],
        "routine": [
            "可测需求|触发条件+系统行为+量化指标+异常边界|‘快速、友好’需转成测量判据|95%查询在2秒内返回，数据量与环境写清",
            "边界值测试|有效类、无效类、边界内、边界、边界外相邻值|1~100整数至少覆盖0、1、2、99、100、101及非整数|不要只测典型有效值",
            "变更控制|提交→影响分析→审批→实现→回归→基线/追踪更新|紧急也要有回退和留痕|直接覆盖线上文件不可审计且难恢复",
        ],
        "short": "为何高内聚低耦合有利于需求变更？评分句：高内聚让相关职责集中，低耦合减少模块间依赖；需求变化时修改范围更局部、连锁影响更小，便于测试维护，但不意味着模块完全不通信。",
        "alerts": ["敏捷不等于不要文档、设计和测试", "测试只能发现缺陷存在，不能证明绝对无缺陷", "需求冲突应分析协商并记录，不能擅自拍板"],
    },
    "信息安全": {
        "recall": [
            "对一个登录系统分别提出机密性、完整性、可用性、可审计性控制。",
            "口述识别—保护—检测—响应—恢复闭环，并给每阶段一个措施。",
            "区分哈希、对称加密、非对称加密、数字签名的目标和密钥使用。",
            "写出事件响应顺序：报告记录—分析—隔离—取证—根除—恢复监控—复盘。",
        ],
        "compare": [
            "加密 vs 哈希 vs 签名|加密保护机密性且可解密；哈希生成摘要用于完整性；签名用私钥签、公开密钥验|哈希不是加密，签名通常不隐藏正文",
            "认证 vs 授权 vs 审计|认证确认是谁；授权决定能做什么；审计记录做了什么|登录成功不代表拥有所有权限",
            "病毒 vs 木马 vs 蠕虫|病毒依附宿主传播；木马伪装/后门；蠕虫可自我复制跨网络传播|实际恶意代码可混合多种特征",
        ],
        "routine": [
            "风险判断|风险≈威胁可能性×脆弱性影响|资产价值、暴露面和控制有效性都要考虑|高危漏洞若不可达，现实风险可低于暴露的中危漏洞",
            "最小权限|主体只获完成任务所需的最少权限、最短时间|配合职责分离、定期复核和撤权|临时管理员权限到期自动回收",
            "事件处置|先保安全与业务，再隔离遏制并保存证据|不能一上来格式化破坏证据和范围判断|恢复后还要监控、复盘和修补根因",
        ],
        "short": "服务器异常外联并出现未授权登录，如何处置？评分句：先报告记录并研判范围，在授权下隔离遏制、保全日志和镜像证据，再根除原因、从可信备份恢复并持续监控，最后复盘整改；不能立即格式化，以免毁证和遗漏横向影响。",
        "alerts": ["HTTPS保护传输通道，不自动证明网站业务可信", "备份必须验证可恢复且与生产隔离", "安全是持续风险管理，不是安装一次软件即可完成"],
    },
}


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def load_questions() -> list[dict]:
    return json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))


def question_stats(questions: list[dict], subject: str | None) -> tuple[int, Counter, Counter]:
    rows = [q for q in questions if subject and q.get("subject") == subject]
    return len(rows), Counter(q.get("knowledge_point") or "未分类" for q in rows), Counter(q.get("type") or "未知" for q in rows)


def select_drills(questions: list[dict], subject: str | None, count: int = 2) -> list[dict]:
    if not subject:
        return []
    rows = [q for q in questions if q.get("subject") == subject]
    kp_count = Counter(q.get("knowledge_point") or "未分类" for q in rows)
    type_rank = {"简答": 0, "填空": 1, "多选": 2, "单选": 3, "判断": 4}
    rows.sort(key=lambda q: (-kp_count[q.get("knowledge_point") or "未分类"], type_rank.get(q.get("type"), 9), str(q.get("id", ""))))
    chosen, seen = [], set()
    for q in rows:
        kp = q.get("knowledge_point") or "未分类"
        if kp in seen:
            continue
        chosen.append(q)
        seen.add(kp)
        if len(chosen) == count:
            break
    return chosen


def render_radar(total: int, kp: Counter, types: Counter, no_bank: bool) -> str:
    if no_bank:
        return "> 本科目暂未进入题库统计。冲刺优先级按课程核心能力设置；练习后请将错因手写进个人错题清单。"
    top = kp.most_common(5)
    rows = ["| 高频知识点 | 题量 | 占本科题库 |", "|---|---:|---:|"]
    rows.extend(f"| {name} | {number} | {number / total:.1%} |" for name, number in top)
    type_text = "、".join(f"{name}{number}题" for name, number in types.most_common())
    return f"> 本科题库 **{total}题**；题型：{type_text}。先拿下前两项，再补第三至第五项。\n\n" + "\n".join(rows)


def render_question(q: dict, number: int) -> str:
    options = q.get("options") or []
    if isinstance(options, dict):
        option_lines = [f"{key}. {value}" for key, value in options.items()]
    else:
        option_lines = [str(value) for value in options]
    option_text = "\n".join(f"   - {line}" for line in option_lines)
    suffix = f"\n{option_text}" if option_text else ""
    return f"{number}. 【{q.get('type', '题')}·{q.get('knowledge_point', '综合')}】{q.get('stem', '')}{suffix}"


def render_answer(q: dict, number: int) -> str:
    answer = q.get("answer") or ""
    explanation = q.get("explanation") or ""
    if explanation and explanation != answer:
        return f"{number}. **答案：{answer}**　{explanation}"
    return f"{number}. **答案：{answer}**"


def build_markdown(questions: list[dict]) -> str:
    intro = f"""# 全科临考冲刺训练包

> 生成日期：{date.today().isoformat()}　　范围：{len(COURSES)}门课程　　性质：**主动输出训练，不是三色笔记摘要**

## 这份资料怎么用

冲刺阶段最值钱的动作不是继续阅读，而是把知识从脑中“提取出来”。每科严格限时12分钟：

1. **2分钟看考情雷达**：只确定先后顺序，不展开阅读。
2. **3分钟白纸输出**：遮住资料，回答“10分钟输出清单”中的前两项。
3. **3分钟例题变式**：先写公式、变量含义和条件，再心算微型例题。
4. **2分钟简答口述**：按评分句说完整，不只背名词。
5. **2分钟限时检测**：做题后到本资料末尾统一核对；错题只记“错因+正确触发词”。

本训练包的结构参考了学习科学中证据较强的做法：练习测试与间隔复习、从记忆中主动提取、例题与独立解题交替，以及使用测验定位薄弱点。方法依据：[IES学习指南](https://ies.ed.gov/ncee/wwc/PracticeGuide/1)、[Cornell主动提取与模拟考试建议](https://lsc.cornell.edu/how-to-study/studying-for-and-taking-exams/what-to-do-with-practice-exams/)、[Dunlosky等人的学习技术综述](https://journals.sagepub.com/stoken/rbtfl/Z10jaVH/60XQM/full)。

## 明日考前安排

| 时段 | 任务 | 停止条件 |
|---|---|---|
| 今晚第一轮（约3小时） | 16科各12分钟，完成白纸输出与题库检测 | 每科只标红1个最弱点，不扩展新资料 |
| 今晚第二轮（60分钟） | 重做所有错题，口述16道简答模板 | 能说出“定义/机制/结果/边界”四句 |
| 睡前（20分钟） | 只看公式变量、单位和失分警报 | 不做难偏怪题，保证睡眠 |
| 入场前（15分钟） | 网络子网、容量换算、SQL、三大电子公式与通用简答骨架 | 看完即停，保持稳定 |

## 通用得分骨架

- **计算题**：已知量（统一单位）→公式→变量含义/适用条件→代入→结果单位→数量级检查。
- **简答题**：结论先行→原理或因果链→题干情境落地→限制/例外。每个评分点单独一句。
- **操作/排障题**：安全与备份→确认现象→从公共条件到局部逐层验证→修复→复测与留痕。
- **选择题**：圈出“最、仅、一定、任何、完全”等绝对词；先按定义排错，再看条件边界。

## 公式与单位总闸

- `1 Byte=8 bit`；通信速率通常按1000进位，存储容量题按题干决定1000或1024进位。
- `k=10³，M=10⁶，m=10⁻³，μ=10⁻⁶，n=10⁻⁹`。代入前统一到基本单位。
- `dB=10log10(功率比)`，所以线性功率比=`10^(dB/10)`；不能把30 dB直接当30代入香农公式。
"""
    parts = [intro.strip()]
    answers: list[tuple[str, list[dict]]] = []
    global_number = 1
    for course, subject in COURSES:
        guide = GUIDES[course]
        total, kp, types = question_stats(questions, subject)
        drills = select_drills(questions, subject)
        answers.append((course, drills))
        section = [f'<div class="course-break"></div>\n\n## {course}', "\n### 1. 考情雷达", render_radar(total, kp, types, subject is None)]
        section.extend(["\n### 2. 10分钟白纸输出清单", "\n".join(f"- [ ] {item}" for item in guide["recall"])])
        section.extend(["\n### 3. 易混对比（先说差异维度）", "\n| 对比项 | 一句话判别 | 高频陷阱 |\n|---|---|---|\n" + "\n".join("| " + " | ".join(row.split("|")) + " |" for row in guide["compare"])])
        routine_rows = []
        for row in guide["routine"]:
            name, method, meaning, example = row.split("|")
            routine_rows.append(f"| {name} | {method} | {meaning} | {example} |")
        section.extend(["\n### 4. 得分套路：含义—条件—微型例题", "\n| 任务 | 公式/步骤 | 含义与边界 | 立即检验 |\n|---|---|---|---|\n" + "\n".join(routine_rows)])
        section.extend(["\n### 5. 高频简答：30秒说出评分句", f"> **题目：** {guide['short'].split('评分句：')[0].strip()}\n>\n> **评分句：** {guide['short'].split('评分句：', 1)[1].strip()}"])
        section.extend(["\n### 6. 最后失分警报", "\n".join(f"- ⚠ {item}" for item in guide["alerts"])])
        section.append("\n### 7. 题库限时检测（答案在文末）")
        if drills:
            rendered = []
            for q in drills:
                rendered.append(render_question(q, global_number))
                global_number += 1
            section.append("\n\n".join(rendered))
        else:
            section.append("1. 【输出题】给定一个系统，分别用反例或判据检查线性、时不变、因果和稳定，并写出卷积输出表达式。")
        parts.append("\n".join(section))

    parts.append('<div class="course-break"></div>\n\n## 题库限时检测答案与错因登记')
    number = 1
    for course, drills in answers:
        parts.append(f"### {course}")
        if not drills:
            parts.append("1. **自评要点：** 线性用叠加性；时不变用输入移位与输出移位比较；因果看是否依赖未来输入；LTI稳定看冲激响应是否绝对可积/可和；输出为 `y=x*h`。")
            continue
        for q in drills:
            parts.append(render_answer(q, number))
            number += 1
    parts.append("""## 最后一页：错因只记这一行

| 科目/题号 | 我的错误触发词 | 正确规则（不超过20字） | 明早是否会做 |
|---|---|---|---|
|  |  |  | □ |
|  |  |  | □ |
|  |  |  | □ |
|  |  |  | □ |

> 到此停止扩展。剩余时间优先睡眠、饮水、准备证件与考试用品。""")
    return "\n\n".join(parts).strip() + "\n"


CSS = r"""
@page { size: A4; margin: 14mm 14mm 16mm; }
* { box-sizing: border-box; }
html { color: #182230; background: #fff; }
body { max-width: 182mm; margin: 0 auto; font: 9.5pt/1.52 "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1, h2, h3 { color: #123b63; page-break-after: avoid; }
h1 { margin: 0 0 5mm; padding-bottom: 3mm; border-bottom: 2px solid #176b87; font-size: 22pt; }
h2 { margin: 6mm 0 3mm; padding: 2mm 3mm; border-left: 4px solid #1d7797; background: #eaf5f8; font-size: 15pt; }
h3 { margin: 4mm 0 2mm; font-size: 11.5pt; }
p { margin: 0 0 2mm; }
ul, ol { margin: 1mm 0 2.5mm; padding-left: 6mm; }
li { margin: 1mm 0; }
strong { color: #0d3858; }
code { padding: .2mm .8mm; border: 1px solid #d4e1e6; border-radius: 3px; background: #f3f7f9; color: #8b3024; font: .92em Consolas, "Microsoft YaHei", monospace; }
blockquote { margin: 2.5mm 0; padding: 2.2mm 3.5mm; border-left: 4px solid #d28a1d; background: #fff7e7; color: #463714; }
table { width: 100%; border-collapse: collapse; margin: 2.5mm 0; font-size: 8.5pt; }
th, td { padding: 1.6mm; border: 1px solid #ccd9df; vertical-align: top; }
th { background: #e7f2f6; color: #153d59; }
.course-break { break-before: page; page-break-before: always; }
a { color: #145a83; text-decoration: none; }
@media print { h1, h2, h3, blockquote, pre, table { break-inside: avoid; } p, li { orphans: 2; widows: 2; } }
"""


def build_html(markdown_text: str) -> str:
    body = markdown.Markdown(extensions=("extra", "sane_lists", "toc")).convert(markdown_text)
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全科临考冲刺训练包</title><style>{CSS}</style></head><body>{body}</body></html>'


def find_browser() -> Path:
    for executable in (*EDGE_CANDIDATES, *CHROME_CANDIDATES):
        if executable.is_file():
            return executable
    for name in ("msedge", "chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError("未找到可用于生成PDF的 Edge/Chrome 浏览器")


def print_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    # Keep the headless profile inside the writable repository.  Some managed
    # environments deny Chromium access to the account-wide temporary folder.
    profile = tempfile.mkdtemp(prefix=".crash-pack-browser-", dir=ROOT)
    try:
        command = [str(browser), "--headless", "--disable-gpu", "--disable-extensions", "--disable-breakpad", "--disable-crash-reporter", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw", f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
        completed = subprocess.run(command, capture_output=True, timeout=120)
        if completed.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size < 10_000:
            details = (completed.stderr or completed.stdout).decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"PDF生成失败（exit={completed.returncode}）：{details}")
    finally:
        # Chromium can keep Crashpad handles briefly after the parent exits.
        # A best-effort cleanup avoids turning a valid PDF into a failed build.
        shutil.rmtree(profile, ignore_errors=True)


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="生成题库驱动的全科临考冲刺训练包")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "全科临考冲刺训练包.md"
    html_path = output_dir / "全科临考冲刺训练包.html"
    pdf_path = output_dir / "全科临考冲刺训练包.pdf"
    text = build_markdown(load_questions())
    markdown_path.write_text(text, encoding="utf-8", newline="\n")
    html_path.write_text(build_html(text), encoding="utf-8", newline="\n")
    print_pdf(find_browser(), html_path, pdf_path)
    print(f"已生成：{pdf_path}")
    print(f"结构：题库考频 + 白纸提取 + 易混对比 + 例题变式 + 简答评分句 + 限时检测")
    print(f"科目数：{len(COURSES)}；PDF大小：{pdf_path.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
