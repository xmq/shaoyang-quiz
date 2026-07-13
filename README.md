# 邵阳备考 · 大学课程学习平台

面向大学课程学习和期末复习的平台，按“讲义理解 → 三色笔记主动回忆 → 题库检验 → 到期复习”的闭环组织内容。

## 当前内容

- 题库总量：**2210 道**（已按同科规范化题干去重）。
- 高校公开资料改编：**225 道**，15 门课程各 15 道；每题保留来源标题、链接、对应考点与改编说明。
- 大学期末原创补充：**184 道**，覆盖全部 15 门讲义课程。
- 题型：单选、多选、判断、填空；全部题目带答案和文字解析。
- 18 个题库科目分类，支持科目、题型、来源和章节筛选。
- 15 门零基础讲义用于系统学习概念、原理和例题。
- 15 门三色笔记用于考前压缩记忆：红色标核心必背与结论，蓝色标公式、步骤和踩分词，黑色标条件、解释和易错点。
- 编程语言主线已统一为 **C 语言 + Python 3**；34 道只考 Visual Basic 的旧题已从刷题库移除。
- 办公软件按 **Microsoft Office + WPS Office** 共性主线讲解，并单列格式兼容、菜单差异与版本边界。
- 四门电子通信课程各有 24 道独立期末训练题；其他 11 门课程各有 8 道针对性补充题。
- 错题自动收集，连续答对 2 次后出本；按固定默认间隔安排再次练习，支持错因归类、收藏、纠错标记和进度导入导出。
- 支持 PWA 离线使用以及 PC、手机浏览器。

## 使用方法

1. 打开 `index.html`，由学习状态卡选择下一步，或从课程卡直达某门课的三个模块。
2. 打开 `notes.html`，先用零基础讲义理解概念、原理和例题。
3. 打开 `color-notes.html`，先遮住内容主动回忆，再核对结论、得分词和易错点。
4. 打开 `quiz.html`，在科目中选择课程；先顺序练习，基础稳定后使用交错练习，按到期复习修正薄弱点。
5. 三个模块的职责与完整性判断见 `三模块学习说明与完整性边界.md`。
6. 计算题应在草稿纸写公式、代入、单位与结论，再选择答案。
7. 题型依据与公开课程来源见 `大学期末题型与习题建设说明.md`。
8. 需要闭卷计时时，使用 `十五科大学期末模拟小卷.md`，做完前半部分后再查看后半部分答案。

## 文件结构

- `index.html` / `home.js` / `home-data.js`：学习平台首页、课程入口与学习状态推荐。
- `quiz.html` / `app.js`：刷题、错题、交错练习、到期复习与进度管理。
- `notes.html` / `零基础讲义完整版.md`：零基础讲义生成物。
- `color-notes.html` / `三色笔记完整版.md`：三色笔记生成物。
- `style.css`：平台首页与刷题界面样式。
- `questions.json`：原始题库数据。
- `questions.js`：浏览器直接加载的同步题库。
- `course_notes/*.md`：15 门课程讲义的唯一可编辑数据源。
- `course-index.json`：课程顺序和文件索引。
- `color_notes/*.md`：15 门课程三色笔记的唯一可编辑数据源。
- `color-notes-index.json`：三色笔记课程顺序和文件索引。
- `notes.template.html` / `build_notes.py`：两个学习页面共用的模板和构建脚本。
- `scripts/add_university_final_bank.py`：大学期末习题与模拟小卷的可重复构建脚本。
- `scripts/merge_university_exam_bank.py`：校验15科高校改编题，执行范围清理、精确/高相似去重并合入主库。
- `大学期末改编题来源汇总.md`：37个高校官方公开大纲、样卷和考试资料来源汇总。
- `大学期末题库去重报告.md`：VB范围清理、旧库重复和新题入库数量审计。
- `大学期末题型与习题建设说明.md`：各科期末考核依据与题型矩阵。
- `三模块学习说明与完整性边界.md`：讲义、三色笔记与习题训练的职责及完整性说明。
- `十五科大学期末模拟小卷.md`：15门课程的闭卷小卷及分离式答案讲评。
- `scripts/validate_questions.py`：题库结构、答案和同步校验。
- `scripts/build_release.py` / `build-meta.js`：发布资源校验与统一版本号。
- `sw.js` / `manifest.webmanifest`：PWA 离线安装支持。

## 内容构建与校验

```powershell
python scripts/add_university_final_bank.py
python scripts/merge_university_exam_bank.py
python scripts/validate_questions.py
python build_notes.py
python scripts/build_home_data.py
python scripts/build_release.py

python build_notes.py --check
python scripts/build_home_data.py --check
python scripts/merge_university_exam_bank.py --check
python scripts/build_release.py --check
```

高校官方期末样卷、课程大纲、考试大纲和考核资料只用于分析范围、题型和能力层次；“大学期末改编”与“大学期末原创”题均重新设置题干、数据、选项和解析，不整卷转载，也不宣称225题逐字来自期末原卷。

## 本地数据安全

- 应用为纯前端，无后台上传。
- 学习进度保存在浏览器 `localStorage` 中。
- 清理浏览器数据前请先导出进度备份。
