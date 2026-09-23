"""Render exam evidence and course scope from reviewed local records."""

import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def render():
    exams = json.loads((ROOT / "exam-sources.json").read_text(encoding="utf-8"))
    guide = json.loads((ROOT / "course-guide.json").read_text(encoding="utf-8"))
    esc = html.escape
    sources = []
    for source in exams["sources"]:
        parts = source["written_parts"]
        split = "、".join(f"{key} {value}%" for key, value in parts.items()) if parts else "未记录可用的分值比例"
        sources.append(
            f'<article id="{esc(source["id"])}"><h3>{esc(source["region"])} · {source["year"]}</h3>'
            f'<p><a href="{esc(source["url"])}" target="_blank" rel="noopener noreferrer">{esc(source["title"])}</a> · {esc(source["kind"])}</p>'
            f'<p><strong>适用范围：</strong>{esc(source["applies_to"])}</p>'
            f'<p>{esc(source["finding"])}</p><p><strong>笔试结构：</strong>{esc(split)}</p>'
            f'<p class="muted">{esc(source["limit"])}</p></article>'
        )
    rows = []
    for course in guide["courses"]:
        route = quote(course["name"])
        rows.append(
            f'<tr><th scope="row">{esc(course["name"])}</th><td>{esc(course["group"])}</td>'
            f'<td>{esc(course["focus"])}</td><td>待核实</td>'
            f'<td><a href="./notes.html#course={route}">讲义</a> · '
            f'<a href="./color-notes.html#course={route}">重点与易错</a></td></tr>'
        )
    coverage = "".join(f'<li><strong>{esc(region)}</strong>：{esc(status)}</li>' for region, status in exams["coverage"].items())
    refs = "".join(
        f'<li><a href="{esc(ref["url"])}" target="_blank" rel="noopener noreferrer">{esc(ref["title"])}</a>：{esc(ref["use"])}</li>'
        for ref in guide["references"]
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#143b6b"><title>湖南考情与科目范围 · 刷题器</title><link rel="manifest" href="./manifest.webmanifest">
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f7fb;color:#203047;font:16px/1.8 system-ui,sans-serif}}
main{{max-width:1040px;margin:auto;padding:24px 20px 60px}}nav{{display:flex;gap:20px;flex-wrap:wrap}}
a{{color:#1857a4;text-underline-offset:3px}}h1{{font-size:28px}}h2{{margin-top:36px;font-size:22px}}h3{{margin:0;font-size:18px}}
.notice,article{{background:white;border:1px solid #dbe3ed;border-radius:12px;padding:18px 22px;margin:16px 0}}
.notice{{border-left:4px solid #1857a4}}.muted{{color:#546377}}p{{margin:10px 0}}li{{margin:8px 0}}
.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:750px;background:white}}
th,td{{border:1px solid #dbe3ed;padding:12px;text-align:left;vertical-align:top}}thead{{background:#eaf0f8}}
td:nth-child(3){{min-width:300px}}td:last-child{{min-width:150px}}
@media(prefers-color-scheme:dark){{body{{background:#101828;color:#edf2f7}}.notice,article,table{{background:#182230;border-color:#344054}}th,td{{border-color:#344054}}thead{{background:#243550}}a{{color:#a8c7ff}}.muted{{color:#bdc7d6}}}}
</style></head><body><main>
<nav aria-label="页面导航"><a href="./index.html">← 选择课程</a><a href="#courses">科目范围</a><a href="#sources">考情依据</a><a href="#coverage">地区覆盖</a></nav>
<h1>湖南考情与科目范围</h1><p class="muted">核对日期：{esc(exams['checked_at'])} · {esc(exams['status'])}</p>
<div class="notice"><strong>先确认岗位考什么，再选择学习内容。</strong><p>{esc(exams['weight_note'])}</p>
<p>目前收录可核验完整专业试卷 {exams['complete_paper_count']} 套。公告能说明部分笔试结构，但不能据此推出网络、数据库、操作系统等各占多少分。</p></div>
<h2>三个比例分别看</h2><ul><li>笔试在招聘总成绩中的比例：用于成绩合成。</li><li>专业知识在笔试中的比例：用于区分公基、写作与专业知识。</li><li>各科在专业卷中的比例：需要明确大纲或完整试卷，才可统计。</li></ul>
<p>现有题库题量、大学学分和资料篇幅都不能替代第三种比例。本工具聚焦普通计算机与电子通信相关岗位，不收录教师方向。</p>
<h2 id="courses">科目范围与内容深度</h2><p>{esc(guide['notice'])} 下表是课程组织，不是排名或学习时间安排。</p>
<div class="table-wrap" tabindex="0" aria-label="科目范围表，可横向滚动"><table><thead><tr><th>课程</th><th>方向</th><th>学习内容</th><th>考试占比</th><th>入口</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2 id="sources">已核对的公开依据</h2>{''.join(sources)}
<h2 id="coverage">14个市州的资料覆盖</h2><p>待收集只表示本项目尚未核实，不表示当地不考或没有相关招聘。</p><ul>{coverage}</ul>
<h2>大学课程结构参考</h2><p>以下资料用于课程覆盖对照，不作为招聘考频证据；讲义和例题为自行整理，不是教材全文摘录。</p><ul>{refs}</ul>
<h2>后续如何补齐占比</h2><p>完整试卷先记录年份、地区、单位、岗位和满分，再按实际分值归入科目及知识点；跨科题分配得分点，避免重复计分。每套先算比例，再报告样本数量、年份和差异；残缺回忆题单列，不与完整卷混算。</p>
</main></body></html>'''


if __name__ == "__main__":
    output = ROOT / "dist" / "exam-guide.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(), encoding="utf-8", newline="\n")
    print(f"已生成 {output}")
