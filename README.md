# 计算机 · 刷题器

面向 **计算机岗位考试** 的移动端刷题与讲义工具。

- 总题量：**1854 道**（超格 1041 + 中公 352 + 德阳 394 + 网络 37 + 软件工程新增 15 + 大数据新增 15）
- 题型：单选 / 多选 / 判断 / 填空
- 13 个科目分类
- 支持科目 / 题型 / 来源 / 章节筛选
- 支持题干、选项、解析全文搜索
- 全部题目均带答案和文字解析
- 错题自动收集 + 连续答对 2 次出本
- 支持题目纠错标记和标记导出
- 支持首页总览、错题分级、今日复习队列
- 支持 PWA 离线安装
- 本地 localStorage 保存进度，支持进度导入 / 导出
- 导入前自动保留设备内备份，可从数据菜单恢复
- 内置 11 门课程的三色笔记，支持课程搜索、章内搜索和折叠目录
- 支持 PC / 手机浏览器

## 在线访问

直接打开 `index.html`，或部署到 GitHub Pages 后通过 https URL 访问。

## 文件结构

- `index.html`：页面骨架
- `style.css`：界面样式
- `app.js`：刷题逻辑
- `questions.js`：浏览器直接加载的题库
- `questions.json`：原始题库数据
- `course_notes/*.md`：11 门课程的讲义单一数据源
- `course-index.json`：课程顺序和文件索引
- `notes.template.html`：讲义页面模板
- `build_notes.py`：从课程 Markdown 生成 `notes.html` 和总讲义 Markdown
- `build-meta.js`：由发布脚本生成的统一内容版本号
- `scripts/build_release.py`：校验发布资源并生成统一版本号
- `sw.js` / `manifest.webmanifest`：PWA 离线安装支持

更新题库后，在上一级工作目录执行 `python validate_questions.py` 校验，再执行 `python build_web_assets.py` 同步 `web/questions.json` 和 `web/questions.js`。更新课程笔记后，在本目录执行 `python build_notes.py`。全部内容定稿后执行 `python scripts/build_release.py` 生成统一版本号；提交前运行 `python build_notes.py --check`、`python scripts/build_release.py --check` 和 `python scripts/validate_questions.py`。

课程内容以 `course_notes/*.md` 为唯一可编辑源；`notes.html`、`讲义三色笔记.md` 以及工作区 `source` 中用于分发的 DOCX 均视为生成物，不应直接分叉编辑。

## 数据来源

- 超格教育「言蹊」全套讲义
- 中公教育招聘专项题
- 德阳事业单位计算机题本
- 网络补充题
- 软件工程与大数据补充题

## 本地数据安全

- 纯前端，无后端，无数据上传
- 所有进度存在浏览器 localStorage
