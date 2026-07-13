# 邵阳备考 · 事业单位专业知识备考平台

面向事业单位专业知识备考，按“讲义理解 → 三色回忆主动提取 → 专项刷题检验 → 到期复习巩固”的闭环组织内容。重点覆盖基础概念、特点与要素、作用与流程、判断与简答得分点，以及少量一步计算。

## 当前内容

- 题库总量：**2210 道**，已按同科规范化题干去重。
- 题型包括单选、多选、判断和填空，全部题目带答案与文字解析；计算题以公式选择、直接代入和单位判断为主。
- 公开题库聚焦基础与常见题型，已隐藏偏复杂综合计算题；首页题量、科目统计、搜索和复习范围均按公开题集计算。
- 15 个零基础讲义科目用于系统理解概念、原理、特点、作用和基础例题。
- 15 个三色回忆科目采用“先答后看”：红色核对最小答案，蓝色核对方法与步骤，黑色核对条件、反例和易错点。
- 讲义与三色回忆单列判断依据、简答关键词和基础计算步骤，便于从“看懂”过渡到“能答”。
- 编程语言主线为 **C 语言 + Python 3**；办公软件按 **Microsoft Office + WPS Office** 的共性操作讲解，并提示格式兼容、菜单差异和版本边界。
- 错题自动收集，连续答对 2 次后出本；系统按固定默认间隔安排重练，并支持错因归类、收藏、纠错标记和进度导入导出。
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

1. 打开 `index.html`，从学习状态卡接受下一步建议，或按科目选择一个小知识单元。
2. 打开 `notes.html`，先理解“是什么、有什么特点、由哪些要素组成、起什么作用”；计算内容同时写出公式、条件和单位。
3. 打开 `color-notes.html`，先口述或默写，再揭示三色答案核对得分词、步骤和边界。
4. 打开 `quiz.html`，首轮按科目与章节顺序练习；基础稳定后使用交错练习，并优先处理错题和到期题。
5. 每次错误只标记一个主要原因：概念、方法、条件、计算或遗忘；完成修正后再进入下一知识点。

## 三个学习模块

| 模块 | 主要任务 | 完成标准 |
| --- | --- | --- |
| 讲义 | 建立知识结构，理解概念、特点、作用、流程和公式 | 能用自己的话解释，并能完成例题的关键步骤 |
| 三色回忆 | 脱离原文主动提取 | 能说出最小答案、得分词、方法和适用条件 |
| 刷题 | 用选择、判断、填空和一步计算检验掌握 | 能说明答案依据，并能定位错误原因 |

三个模块不是三份重复资料：讲义负责“学懂”，三色回忆负责“记牢”，刷题负责“会答并纠错”。

## 文件结构

- `index.html` / `home.js`：平台首页、科目入口与学习状态推荐。
- `quiz.html` / `app.js`：专项刷题、错题、交错练习、到期复习与进度管理。
- `course_notes/*.md`：15 个科目讲义的唯一可编辑数据源。
- `color_notes/*.md`：15 个科目三色回忆内容的唯一可编辑数据源。
- `notes.template.html` / `build_notes.py`：讲义和三色回忆页面的模板与生成器。
- `style.css`：平台首页与刷题界面样式。
- `questions.json`：题库唯一可编辑数据源；构建时转换为浏览器使用的 `questions.js`。
- `course-index.json` / `color-notes-index.json`：科目顺序和文件索引。
- `scripts/build_site.py`：将运行文件、生成页面和媒体汇总到 `dist/`。
- `scripts/validate_questions.py`：题库结构、答案与同步校验。
- `scripts/build_release.py`：发布资源校验与统一版本号生成。
- `sw.js` / `manifest.webmanifest`：PWA 离线安装支持。

## 内容构建与校验

```powershell
# 修改讲义或三色回忆内容后重新生成页面
python build_notes.py --target all

# 构建完整网站发布包
python scripts/build_site.py --output dist

# 发布前校验
python scripts/validate_questions.py --js dist/questions.js
python scripts/validate_color_notes.py
python scripts/build_release.py --asset-root dist --check
```

`dist/` 采用发布白名单，只包含 HTML、CSS、浏览器脚本、站点图标和题目配图。浏览器运行资源、讲义页面、三色回忆页面、首页索引和发布版本号均在构建时生成，不提交到版本库。

## GitHub Pages 发布

本仓库的 Pages 由 **GitHub Actions** 构建。推送到 `main` 后自动校验并发布；也可以在 Actions 中手动运行 `Deploy Pages`。若重新创建 Pages 站点，应在仓库 **Settings → Pages** 中将 **Build and deployment → Source** 设为 **GitHub Actions**。

## 本地数据安全

- 应用为纯前端，无后台上传。
- 学习进度保存在浏览器 `localStorage` 中。
- 清理浏览器数据前请先导出进度备份。
