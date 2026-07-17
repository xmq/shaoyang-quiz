"""Build the all-subject crash-review Markdown, HTML and PDF."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
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


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def load_courses() -> list[tuple[str, str]]:
    index_path = ROOT / "color-notes-index.json"
    items = json.loads(index_path.read_text(encoding="utf-8"))
    courses: list[tuple[str, str]] = []
    for item in items:
        name = str(item["name"])
        path = ROOT / str(item["file"])
        courses.append((name, path.read_text(encoding="utf-8").strip()))
    return courses


def build_markdown(courses: list[tuple[str, str]]) -> str:
    course_names = "、".join(name for name, _ in courses)
    intro = f"""# 全科综合冲刺笔记

> 生成日期：{date.today().isoformat()}　　范围：{len(courses)} 门课程

本笔记用于考试前最后一轮复习，按“红色高频 → 蓝色补分 → 黑色防漏 → 公式释义 → 简答模板”的顺序组织。覆盖科目：{course_names}。

## 最后一天使用方法

1. 第一轮只看每科红色考点和公式，确保能口述概念、条件和变量含义。
2. 第二轮看蓝色考点与简答模板，遮住答案后用“定义—原理—作用—边界”四步复述。
3. 第三轮只检查易错边界、单位、适用条件和曾经做错的题，不再扩展新内容。
4. 计算题先写公式和各量含义，再统一单位、代入、验算；只有结果没有过程容易丢步骤分。

## 通用简答题模板

- **概念题**：先给准确定义，再写核心组成或特征，最后写用途与易错边界。
- **比较题**：按“共同点—差异维度—适用场景”作答，至少比较原理、性能和使用条件。
- **作用题**：写“解决什么问题—通过什么机制—得到什么效果—有什么限制”。
- **流程题**：使用箭头写完整顺序，再为每一步补一句功能，避免只列名词。
- **故障题**：按“现象—可能原因—验证手段—处理措施—复测”闭环作答。

## 高频单位换算

- `1 Byte=8 bit`；存储容量常按 `1 KB=1024 Byte`，通信速率常按 `1 kbit/s=1000 bit/s`，以题目口径为准。
- `1 ms=10^-3 s`，`1 μs=10^-6 s`，`1 ns=10^-9 s`；`1 kHz=10^3 Hz`，`1 MHz=10^6 Hz`。
- 电路中 `1 kΩ=10^3 Ω`，`1 mA=10^-3 A`，`1 μF=10^-6 F`；代公式前必须换成同一数量级。
- 公式中的对数若写 `log₂` 表示以2为底；分贝功率比换算使用 `S/N=10^(dB/10)`。
"""

    sections = [intro.strip()]
    for name, text in courses:
        sections.append(f'<div class="course-break"></div>\n\n{text}')
    return "\n\n".join(sections).strip() + "\n"


CSS = r"""
@page { size: A4; margin: 16mm 15mm 17mm; }
* { box-sizing: border-box; }
html { color: #172033; background: #fff; }
body {
  max-width: 180mm; margin: 0 auto; color: #172033;
  font: 10.4pt/1.62 "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1, h2, h3 { color: #123b63; page-break-after: avoid; }
h1 { margin: 0 0 5mm; padding-bottom: 3mm; border-bottom: 2px solid #1e6b8f; font-size: 23pt; }
h2 { margin: 7mm 0 3mm; padding: 2.2mm 3mm; border-left: 4px solid #277da1; background: #eef7fa; font-size: 15.5pt; }
h3 { margin: 5mm 0 2mm; font-size: 12.2pt; }
p { margin: 0 0 2.5mm; }
ul, ol { margin: 1.5mm 0 3mm; padding-left: 6mm; }
li { margin: 1.2mm 0; }
strong { color: #0f3555; }
code {
  padding: .25mm 1mm; border: 1px solid #d7e4ea; border-radius: 3px;
  background: #f4f8fa; color: #8f2d20; font: .94em Consolas, "Microsoft YaHei", monospace;
}
blockquote {
  margin: 3mm 0; padding: 2.5mm 4mm; border-left: 4px solid #d89a2b;
  background: #fff8e8; color: #4d3b16;
}
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 9pt; }
th, td { padding: 2mm; border: 1px solid #cfdce2; vertical-align: top; }
th { background: #e9f3f7; color: #153d5a; }
.course-break { break-before: page; page-break-before: always; }
.red, p:has(> strong:first-child) { break-inside: avoid; }
a { color: #145a83; text-decoration: none; }
@media print {
  h1, h2, h3, blockquote, pre, table { break-inside: avoid; }
  p, li { orphans: 2; widows: 2; }
}
"""


def build_html(markdown_text: str) -> str:
    converter = markdown.Markdown(extensions=("extra", "sane_lists", "toc"))
    body = converter.convert(markdown_text)
    title = "全科综合冲刺笔记"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>{body}</body>
</html>
"""


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
    with tempfile.TemporaryDirectory(prefix="crash-notes-browser-") as profile:
        command = [
            str(browser),
            "--headless",
            "--disable-gpu",
            "--disable-extensions",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        completed = subprocess.run(command, capture_output=True, timeout=120)
        if completed.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size < 10_000:
            raw_details = completed.stderr or completed.stdout
            details = raw_details.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"PDF生成失败（exit={completed.returncode}）：{details}")


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="生成全科综合冲刺笔记PDF")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "全科综合冲刺笔记.md"
    html_path = output_dir / "全科综合冲刺笔记.html"
    pdf_path = output_dir / "全科综合冲刺笔记.pdf"

    courses = load_courses()
    markdown_text = build_markdown(courses)
    html_text = build_html(markdown_text)
    markdown_path.write_text(markdown_text, encoding="utf-8", newline="\n")
    html_path.write_text(html_text, encoding="utf-8", newline="\n")
    print_pdf(find_browser(), html_path, pdf_path)

    print(f"已生成：{pdf_path}")
    print(f"科目数：{len(courses)}；PDF大小：{pdf_path.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
