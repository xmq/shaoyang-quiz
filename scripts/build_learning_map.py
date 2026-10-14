"""Build stable chapter/topic records for every course from the maintained notes."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from topic_exam_guidance import guidance_for, validate_guidance

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "learning-map.json"

COURSES = {
    "Office软件操作": ("office", "办公软件"),
    "大学计算机基础与新技术": ("computer-foundations", "计算机基础"),
    "多媒体技术": ("multimedia", "多媒体"),
    "操作系统原理": ("operating-system", "操作系统"),
    "数据库技术": ("database", "数据库"),
    "数据结构与算法": ("data-structures", "算法与数据结构"),
    "C与Python程序设计": ("programming", "编程语言"),
    "计算机组成原理": ("computer-organization", "计算机组成原理"),
    "计算机网络": ("computer-network", "计算机网络"),
    "电路分析与电工技术": ("circuit", "电路分析与电工技术"),
    "模拟电子技术": ("analog-electronics", "模拟电子技术"),
    "数字电子技术": ("digital-electronics", "数字电子技术"),
    "通信原理与高频电子线路": ("communication", "通信原理与高频电子线路"),
    "信号与系统": ("signals-systems", "信号与系统"),
    "软件工程": ("software-engineering", "软件工程"),
    "信息安全": ("information-security", "信息安全"),
}

COURSE_SUBJECTS = {
    "大学计算机基础与新技术": ("计算机基础", "信息基础", "大数据"),
}

EXTRA_TOPIC_KEYWORDS = {
    "操作系统原理": {
        "操作系统功能与基本特征": ["操作系统", "批处理", "分时", "实时", "并发", "并行", "共享", "虚拟", "异步"],
        "用户态、内核态与系统调用": ["用户态", "内核态", "系统调用", "特权指令", "中断", "异常", "宏内核", "微内核"],
        "进程、线程与PCB": ["进程", "线程", "PCB", "程序", "地址空间", "寄存器", "进程控制块"],
        "进程状态与切换": ["就绪", "运行态", "阻塞", "等待态", "状态转换", "上下文切换", "I/O完成"],
        "处理机调度": ["调度", "FCFS", "SJF", "优先级", "时间片", "RR", "周转时间", "等待时间", "甘特图"],
        "同步、互斥与信号量": ["同步", "互斥", "信号量", "P操作", "V操作", "临界区", "生产者", "消费者", "读者写者"],
        "死锁条件与处理": ["死锁", "互斥条件", "请求并保持", "不剥夺", "循环等待", "死锁预防", "死锁检测"],
        "银行家算法与安全序列": ["银行家", "安全序列", "安全状态", "不安全状态", "Available", "Allocation", "Need", "Max"],
        "连续分配、分页与分段": ["连续分配", "首次适应", "最佳适应", "最坏适应", "内部碎片", "外部碎片", "分页", "分段", "页表", "TLB", "逻辑地址", "物理地址"],
        "虚拟存储与页面置换": ["虚拟存储", "虚拟内存", "缺页", "页面置换", "OPT", "FIFO", "LRU", "CLOCK", "Belady", "抖动", "局部性"],
        "文件组织、目录与链接": ["文件", "目录", "FCB", "inode", "连续分配", "链接分配", "索引分配", "硬链接", "符号链接", "位示图"],
        "I/O控制、缓冲与SPOOLing": ["程序查询", "中断方式", "DMA", "通道", "缓冲", "SPOOLing", "设备驱动", "设备控制器", "打印队列"],
        "磁盘调度": ["磁盘调度", "磁道", "磁头", "寻道", "SSTF", "SCAN", "LOOK", "C-SCAN", "FCFS"]
    },
    "数据结构与算法": {
        "数据结构与复杂度": ["逻辑结构", "存储结构", "抽象数据类型", "ADT", "时间复杂度", "空间复杂度", "递归复杂度", "大O"],
        "顺序表": ["线性表", "顺序表", "数组插入", "数组删除", "随机访问", "动态数组"],
        "链表": ["链表", "单链表", "双链表", "循环链表", "头结点", "前驱", "指针插入", "指针删除"],
        "栈与递归": ["栈", "入栈", "出栈", "括号匹配", "表达式", "递归", "调用栈"],
        "队列与循环队列": ["队列", "循环队列", "front", "rear", "先进先出", "假溢出"],
        "串与KMP": ["字符串", "串", "模式串", "KMP", "next数组", "前缀函数", "模式匹配"],
        "数组、稀疏矩阵与广义表": ["二维数组", "行优先", "列优先", "地址计算", "稀疏矩阵", "三元组", "广义表"],
        "二叉树性质": ["树", "二叉树", "完全二叉树", "满二叉树", "叶结点", "结点数", "高度", "n0", "n2"],
        "遍历与树的还原": ["先序", "前序", "中序", "后序", "层序", "遍历序列", "还原二叉树", "重建二叉树"],
        "BST与AVL": ["二叉排序树", "二叉搜索树", "BST", "AVL", "平衡二叉树", "旋转", "LL", "RR", "LR", "RL"],
        "堆": ["堆", "大根堆", "小根堆", "上浮", "下沉", "堆顶", "Top K"],
        "哈夫曼树与B/B+树": ["哈夫曼", "WPL", "带权路径", "前缀编码", "B树", "B+树", "多路查找树"],
        "图的存储": ["图", "顶点", "边", "邻接矩阵", "邻接表", "入度", "出度"],
        "DFS与BFS": ["DFS", "BFS", "深度优先", "广度优先", "图遍历", "visited"],
        "最小生成树": ["最小生成树", "生成树", "MST", "Prim", "Kruskal", "铺设线路", "总成本"],
        "最短路径": ["最短路径", "最少边数", "Dijkstra", "Bellman-Ford", "Floyd", "负权边", "松弛"],
        "拓扑排序": ["拓扑排序", "DAG", "有向无环图", "先修", "依赖", "入度为0"],
        "二分查找": ["顺序查找", "折半查找", "二分查找", "low", "high", "mid", "有序表"],
        "散列查找": ["散列", "哈希", "装填因子", "线性探测", "开放定址", "拉链法", "删除标记"],
        "插入、冒泡与选择排序": ["插入排序", "直接插入", "冒泡排序", "选择排序", "简单选择"],
        "快速排序": ["快速排序", "快排", "枢轴", "划分", "partition"],
        "归并排序": ["归并排序", "归并", "有序段", "双指针", "外部排序"],
        "堆、希尔、基数与排序选择": ["堆排序", "希尔排序", "基数排序", "计数排序", "稳定排序", "排序选择", "排序算法"],
        "场景中的结构与算法选择": ["结构选型", "算法选型", "LRU", "Top K", "Trie", "并查集", "动态规划", "贪心", "回溯", "滑动窗口", "场景"]
    },
    "大学计算机基础与新技术": {
        "信息特征与数字素养": ["信息特征", "共享性", "时效性", "真伪性", "价值性", "依附性", "信息素养", "信息伦理"],
        "数制、编码与系统组成": ["二进制", "十六进制", "ASCII", "Unicode", "UTF-8", "CPU", "运算器", "控制器", "RAM", "ROM", "存储器"],
        "文件、软件与常用操作": ["文件", "文件夹", "路径", "Windows", "Linux", "系统软件", "应用软件", "资源管理器"],
        "IaaS、PaaS与SaaS": ["云计算", "IaaS", "PaaS", "SaaS", "虚拟化", "边缘计算", "公有云", "私有云", "混合云"],
        "4V、数据挖掘与分布式处理": ["大数据", "4V", "数据挖掘", "分类算法", "聚类算法", "关联分析", "Hadoop", "HDFS", "MapReduce", "YARN", "Spark", "流处理", "数据仓库"],
        "训练、推理与生成式AI": ["人工智能", "机器学习", "深度学习", "监督学习", "无监督学习", "强化学习", "模型训练", "模型推理", "生成式AI", "神经网络"],
        "感知、网络与物联网平台": ["物联网", "传感器", "执行器", "物联网网关", "感知层", "物联网平台"],
        "区块、共识与智能合约": ["区块链", "区块", "共识机制", "智能合约", "联盟链", "公有链", "私有链"],
        "计算机发展与应用": ["计算机发展", "计算机特点", "科学计算", "数据处理", "过程控制", "辅助设计"],
        "按场景选择技术": ["技术选型", "应用场景", "数字化转型", "信息技术与社会", "信息社会"],
    }
}

KNOWLEDGE_TO_TOPIC = {
    "信息基础": {
        "信息与载体": "信息特征与数字素养", "信息特征": "信息特征与数字素养",
        "信息技术与社会": "计算机发展与应用", "信息素养": "信息特征与数字素养",
    },
    "计算机基础": {
        "数制与编码": "数制、编码与系统组成", "计算机硬件": "数制、编码与系统组成",
        "存储系统": "数制、编码与系统组成", "计算机软件": "文件、软件与常用操作",
        "文件与Windows基础": "文件、软件与常用操作", "计算机发展与应用": "计算机发展与应用",
    },
    "大数据": {
        "Hadoop与HDFS": "4V、数据挖掘与分布式处理", "流处理": "4V、数据挖掘与分布式处理",
        "MapReduce与YARN": "4V、数据挖掘与分布式处理", "数据仓库": "4V、数据挖掘与分布式处理",
        "Spark": "4V、数据挖掘与分布式处理",
    },
    "办公软件": {
        "办公文件与协作": "格式与兼容", "Word文字与段落": "字符、段落与样式",
        "Word长文档排版": "分页、分节与目录", "Excel公式与引用": "引用与函数",
        "Excel数据分析": "筛选、排序与汇总", "PowerPoint演示": "母版、切换与动画",
        "Excel工作簿基础": "按任务组合工具",
    },
    "多媒体": {
        "多媒体系统与应用": "媒体与交互", "图形图像": "像素、颜色与容量",
        "音频数字化": "采样、量化与编码", "多媒体压缩与容量": "无损与有损",
        "动画与视频": "帧率与编码",
    },
    "操作系统": {
        "操作系统基础": "用户态、内核态与系统调用", "进程与线程": "进程、线程与PCB",
        "进程调度与同步": "处理机调度", "死锁": "死锁条件与处理",
        "内存与虚拟存储": "虚拟存储与页面置换", "文件系统": "文件组织、目录与链接",
        "设备与I/O管理": "I/O控制、缓冲与SPOOLing", "Windows系统操作": "操作系统功能与基本特征",
    },
    "数据库": {
        "数据库系统基础": "数据与管理软件", "数据库设计": "实体与联系转换",
        "关系模型与代数": "选择、投影与连接", "SQL查询": "先筛行，再分组",
        "索引与存储": "设计阶段与查询成本", "数据库规范化": "函数依赖与范式",
        "事务与并发控制": "ACID与并发异常",
    },
    "算法与数据结构": {
        "数据结构基础": "数据结构与复杂度", "算法复杂度": "数据结构与复杂度",
        "线性表": "顺序表", "栈与队列": "栈与递归",
        "树与二叉树": "二叉树性质", "图结构与算法": "图的存储",
        "查找与散列": "二分查找", "排序算法": "插入、冒泡与选择排序",
    },
    "编程语言": {
        "程序设计基础": "从算法到执行", "Python数据类型": "类型与存储",
        "程序控制结构": "条件与分支", "C函数与作用域": "参数与返回",
        "C数组与字符串": "下标与共享", "C指针与内存": "地址与资源",
        "C文件与结构体": "错误处理与编码", "程序异常与调试": "错误处理与编码",
    },
    "计算机组成原理": {
        "计算机组成基础": "硬件、软件与性能", "计算机系统性能": "硬件、软件与性能",
        "数据表示与运算": "进制、补码与溢出", "指令系统与CPU": "数据通路与寻址",
        "存储层次与Cache": "层次、容量与Cache", "流水线": "重叠执行与冲突",
        "总线与I/O": "总线带宽和设备传输",
    },
    "电路分析与电工技术": {
        "电路分析基础": "参考方向与功率", "直流电路与功率": "KCL、KVL与等效电阻",
        "一阶动态电路": "初值、终值与时间常数", "正弦交流与RLC": "有效值与相位",
        "三相电路与用电": "串并联系统",
    },
    "模拟电子技术": {
        "模拟电子基础": "模型与工作区", "二极管电路": "导通、整流与稳压",
        "三极管放大": "静态点与失真", "MOSFET": "模型与工作区",
        "负反馈放大": "判断反馈极性", "运算放大器": "虚短、虚断与边界",
        "功率放大": "振荡与输出能力", "直流电源": "导通、整流与稳压",
    },
    "数字电子技术": {
        "数字电子基础": "二进制与编码", "逻辑代数与门电路": "化简与等价",
        "组合逻辑": "从功能到表达式", "触发器": "状态与有效边沿",
        "时序逻辑": "状态数量与容量", "存储与可编程逻辑": "状态数量与容量",
        "A/D与D/A转换": "分辨率与转换", "脉冲与555电路": "从输入求输出",
    },
    "通信原理与高频电子线路": {
        "通信系统基础": "各环节的作用", "信道容量与香农公式": "速率、带宽与信噪比",
        "抽样与PCM": "数字化与载波", "模拟调制": "数字化与载波",
        "数字调制": "接入与资源分配", "高频电路": "调谐与变频",
        "光纤与移动通信": "频率与波长",
    },
    "信号与系统": {
        "信号与系统基础": "时间、幅度与周期", "系统性质": "逐项检验性质",
        "LTI系统与卷积": "输入与冲激响应", "频域分析": "时域与频域",
        "拉普拉斯与Z变换": "变换式与收敛域", "采样定理": "采样条件与抗混叠",
    },
    "软件工程": {
        "软件工程基础": "工程化解决问题", "软件过程模型": "模型选择",
        "需求工程": "需求是否可验证", "软件设计与UML": "职责与依赖",
        "软件测试": "方法、层次与覆盖", "软件维护与配置": "变更可追溯",
        "项目管理": "风险与计划",
    },
    "信息安全": {
        "安全目标与风险": "安全目标与风险", "恶意代码与社会工程": "传播机制与欺骗",
        "身份认证与访问控制": "认证、授权与审计", "密码技术": "加密、摘要与签名",
        "网络安全防护": "边界与检测", "安全事件响应": "防注入与恢复能力",
        "数据备份与恢复": "防注入与恢复能力", "隐私合规与责任": "必要使用与规则核验",
    },
}


def read_structure(course_name: str):
    lines = (ROOT / "color_notes" / f"{course_name}.md").read_text(encoding="utf-8").splitlines()
    chapters = []
    topics = []
    chapter_id = None
    for line in lines:
        if line.startswith("## "):
            chapter_id = f"{COURSES[course_name][0]}.c{len(chapters) + 1:02d}"
            chapters.append({"chapter_id": chapter_id, "title": line[3:].strip()})
        elif line.startswith("### ") and chapter_id:
            topics.append({
                "topic_id": f"{COURSES[course_name][0]}.t{len(topics) + 1:02d}",
                "chapter_id": chapter_id,
                "title": line[4:].strip(),
                "depth": "direct",
                "keywords": [],
                "knowledge_points": [],
            })
    return chapters, topics


def build():
    current = json.loads(OUTPUT.read_text(encoding="utf-8"))
    existing = {course["course_name"]: course for course in current["courses"]}
    order = [item["name"] for item in json.loads((ROOT / "course-index.json").read_text(encoding="utf-8"))]
    courses = []
    for course_name in order:
        if course_name == "计算机网络":
            courses.append(existing[course_name])
            continue
        course_id, subject = COURSES[course_name]
        chapters, topics = read_structure(course_name)
        subjects = COURSE_SUBJECTS.get(course_name, (subject,))
        by_title = {topic["title"]: topic for topic in topics}
        for mapped_subject in subjects:
            for knowledge_point, title in KNOWLEDGE_TO_TOPIC.get(mapped_subject, {}).items():
                if title in by_title:
                    by_title[title]["knowledge_points"].append(knowledge_point)
        for topic in topics:
            words = [part for part in re.split(r"[、，与和及/（）()·]+", topic["title"]) if len(part) >= 2]
            words.extend(token for token in re.findall(r"[A-Za-z0-9+.-]+|[\u4e00-\u9fff]{2,}", topic["title"]) if len(token) >= 2)
            extras = EXTRA_TOPIC_KEYWORDS.get(course_name, {}).get(topic["title"], [])
            keyword_source = extras + topic["knowledge_points"] if course_name in EXTRA_TOPIC_KEYWORDS else words + extras + topic["knowledge_points"]
            topic["keywords"] = list(dict.fromkeys(keyword_source))
        courses.append({
            "course_id": course_id,
            "course_name": course_name,
            "subject": subject,
            "subjects": list(subjects),
            "chapters": chapters,
            "topics": topics,
        })
    topic_ids = {topic["topic_id"] for course in courses for topic in course["topics"]}
    unknown_ids = validate_guidance(topic_ids)
    if unknown_ids:
        raise ValueError(f"题型指引含无效知识点：{', '.join(unknown_ids)}")
    for course in courses:
        course.setdefault("subjects", [course["subject"]])
        for topic in course["topics"]:
            guidance = guidance_for(topic["topic_id"])
            topic.update(guidance)
            topic["depth"] = guidance["target_depth"]
    return {
        "schema_version": 3,
        "scope_policy": "各高校通用教材的共同核心；不纳入学校自编专题、特定软件版本、行业工具专项和高级选修章节。",
        "exam_policy": "通用教材确定知识范围，大学期末资料补充课程任务；湖南笔试回忆只证明某次考试出现过的题型与情境；408仅为数据结构、计算机组成原理、操作系统和计算机网络提供分析深度上限。本站按事业单位深度拆分为概念、说明、计算、应用和代码练习。",
        "courses": courses,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    expected = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("learning-map.json 与课程重点卡不同步")
        print(f"学习地图已同步：{len(payload['courses'])}门课程，{sum(len(course['topics']) for course in payload['courses'])}个知识点")
        return
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"学习地图已更新：{len(payload['courses'])}门课程，{sum(len(course['topics']) for course in payload['courses'])}个知识点")


if __name__ == "__main__":
    main()
