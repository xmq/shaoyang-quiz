# 计算机 · 刷题器

针对 **计算机专业**（5/23 笔试）的本地刷题工具。

- 总题量：**2127 道**（题海训练 214 + 超格 1121 + 中公 380 + 德阳 375 + 网络 37）
- 题型：单选 / 多选 / 判断 / 填空
- 12 个科目分类
- 支持科目 / 题型 / 来源筛选
- 错题自动收集 + 连续答对 2 次出本
- 本地 localStorage 保存进度，支持进度导入 / 导出
- 支持 PC / 手机浏览器

## 在线访问

直接打开 `index.html`，或部署到 GitHub Pages 后通过 https URL 访问。

## 文件结构

- `index.html`：页面骨架
- `style.css`：界面样式
- `app.js`：刷题逻辑
- `questions.js`：浏览器直接加载的题库
- `questions.json`：原始题库数据

更新题库后，在项目根目录执行 `python validate_questions.py` 校验，再执行 `python build_web_assets.py` 同步 `web/questions.json` 和 `web/questions.js`。

## 数据来源

- 超格教育「言蹊」全套讲义
- 中公教育招聘专项题
- 德阳事业单位计算机真题
- 网络爬取补充

## 本地数据安全

- 纯前端，无后端，无数据上传
- 所有进度存在浏览器 localStorage
