# 刷题器

面向湖南省各地事业单位计算机专业知识笔试，按大学课程组织讲义、章节重点和练习。学习时间、顺序和方式由使用者自行安排。

## 2026-09-23 内容重整

- 已移除教师方向及99道教学论题目。其余15科原三色笔记改为“重点与易错”：120个知识章节、121组核心知识／方法与例题／易混易错。颜色表示内容用途，不表示考频。
- 讲义与重点按同名章节互跳；保留默认连续阅读、科目内搜索和可选回忆模式。
- 课程分为计算机专业主干、应用与安全、电子通信扩展，分组不是考试权重或强制学习顺序。
- 新增“湖南考情与科目范围”页面，记录首批6条公开依据及14市州资料覆盖状态。完整专业试卷样本仍为0，暂不提供各学科百分比。
- 课程参考与考试来源分别保存，不把大学课程、培训题量或外地题库冒充湖南考情；页面保留来源原义。
- 现有讲义保留并补充部分原理和例题，尚未完成15科逐段教材级复核；当前内容范围与缺口见 `三模块学习说明与完整性边界.md`。

## 当前内容

- 题库总量：**2432 道**，全部纳入公开练习，已按同科规范化题干去重。
- 题型包括单选1714、多选310、判断286、填空58和简答自评64；全部题目带答案与文字解析。
- 题库聚焦基础与常见题型；首页题量、科目统计、搜索和复习范围均按完整题库计算。每题同时标注知识点、考查能力和难度，便于模拟结果归纳薄弱类型。
- 15 个零基础讲义科目用于系统理解概念、原理、特点、作用和基础例题。
- 15 个重点科目按课程章节组织：红色核心知识、蓝色方法与例题、黑色易混易错。章节重点是学习建议，不是已核实的湖南考频。
- 讲义与重点与易错分别承担“学懂”和“抓重点”的任务，便于从“看懂”过渡到“能答”。
- 编程语言主线为 **C 语言 + Python 3**；办公软件按 **Microsoft Office + WPS Office** 的共性操作讲解，并提示格式兼容、菜单差异和版本边界。
- 错题自动收集，连续答对 2 次后出本；系统按固定默认间隔安排重练，并支持错因归类、收藏、纠错标记和进度导入导出。
- 模拟考试采用交卷后统一判分，支持 20/30/50 题、自动交卷、跳题统计和薄弱能力提示；顺序、随机刷题保留即时反馈。
- 支持 PWA 离线使用以及 PC、手机浏览器。

## 在线与本地使用

线上版本由 GitHub Actions 构建并发布，部署产物只包含浏览器运行所需文件，不暴露内容维护工具和内部资料。

本地预览：

```powershell
python scripts/build_site.py --output dist
python -m http.server 8000 --directory dist
```

然后访问 `http://localhost:8000`。不要直接修改 `dist/`：它是可随时重建、不会提交到 Git 的临时发布目录。

## 建议学习顺序

1. 打开 `index.html`，选择课程进入讲义。
2. 打开 `notes.html`，先理解“是什么、有什么特点、由哪些要素组成、起什么作用”；计算内容同时写出公式、条件和单位。
3. 打开 `color-notes.html`，自行选择章节，核对核心知识、方法与例题、易混易错；需要完整解释时进入本章讲义。
4. 打开 `quiz.html`，选择课程后进行顺序、随机或限时练习，并优先处理该课程的错题和到期题。
5. 每次错误只标记一个主要原因：概念、方法、条件、计算或遗忘；完成修正后再进入下一知识点。

## 三个学习模块

| 模块 | 主要任务 | 完成标准 |
| --- | --- | --- |
| 讲义 | 建立知识结构，理解概念、特点、作用、流程和公式 | 能用自己的话解释，并能完成例题的关键步骤 |
| 重点与易错 | 按章节提炼核心知识、方法和边界 | 能说明结论的条件，并完成典型例子 |
| 刷题 | 用客观题、简答自评和基础应用题检验掌握 | 能说明结论、原因或机制及适用边界 |

三个模块不是三份重复资料：讲义负责“学懂”，重点与易错负责“抓重点”，刷题负责“会答并纠错”。

## 文件结构

- `index.html` / `home.js`：课程菜单与学习入口。
- `quiz.html` / `app.js`：顺序刷题、随机刷题、模拟考试、错题、到期复习与进度管理。
- `course_notes/*.md`：15 个科目讲义的唯一可编辑数据源。
- `color_notes/*.md`：15 个科目重点与易错内容的唯一可编辑数据源。
- `notes.template.html` / `build_notes.py`：讲义和重点与易错页面的模板与生成器。
- `style.css`：平台首页与刷题界面样式。
- `questions.json`：题库唯一可编辑数据源；构建时转换为浏览器使用的 `questions.js`。
- `course-index.json` / `color-notes-index.json`：科目顺序和文件索引。
- `scripts/build_site.py`：将运行文件、生成页面和媒体汇总到 `dist/`。
- `scripts/validate_questions.py`：题库结构、答案与同步校验。
- `scripts/merge_applied_bank.py`：合并并校验基础应用题，检查科目配额、来源字段和重复题干。
- `scripts/merge_supplement_bank.py`：合并薄弱科目与电子实操补充题，并执行来源、题型配额和近似去重检查。
- `scripts/enrich_question_metadata.py`：确定性补齐每题的知识点、能力类别与难度标签。
- `scripts/build_release.py`：发布资源校验与统一版本号生成。
- `exam-sources.json`：已核对考情、适用范围、比例含义及地区覆盖；未知比例使用null。
- `course-guide.json`：课程方向、重点范围、讲解深度及课程参考资料。
- `scripts/build_exam_guide.py`：从上述记录生成考情说明页。
- `sw.js` / `manifest.webmanifest`：PWA 离线安装支持。

## 内容构建与校验

```powershell
# 修改讲义或重点与易错内容后重新生成页面
python build_notes.py --target all

# 构建完整网站发布包
python scripts/build_site.py --output dist

# 发布前校验
python scripts/validate_questions.py --js dist/questions.js
python scripts/validate_color_notes.py
python scripts/validate_course_notes.py
python scripts/build_release.py --asset-root dist --check
```

`dist/` 采用发布白名单，只包含 HTML、CSS、浏览器脚本、站点图标和题目配图。浏览器运行资源、讲义页面、重点与易错页面、首页索引和发布版本号均在构建时生成，不提交到版本库。

`scripts/rebuild_color_notes_frequency.py` 与 `scripts/update_color_notes_by_exam_frequency.py` 已停用，避免用培训题库数量重新覆盖已整理内容。请直接维护Markdown和来源记录，再构建与校验。

## GitHub Pages 发布

本仓库的 Pages 由 **GitHub Actions** 构建。推送到 `main` 后自动校验并发布；也可以在 Actions 中手动运行 `Deploy Pages`。若重新创建 Pages 站点，应在仓库 **Settings → Pages** 中将 **Build and deployment → Source** 设为 **GitHub Actions**。

## 本地数据安全

- 应用为纯前端，无后台上传。
- 学习进度保存在浏览器 `localStorage` 中。
- 清理浏览器数据前请先导出进度备份。
