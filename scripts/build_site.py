"""Build the allow-listed GitHub Pages artifact into dist/."""

from pathlib import Path
import argparse
import json
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_notes  # noqa: E402
from scripts import build_home_data, build_release  # noqa: E402


STATIC_FILES = (
    "index.html",
    "quiz.html",
    "style.css",
    "app.js",
    "home.js",
    "question-media.js",
    "sw.js",
    "manifest.webmanifest",
    "icon.svg",
    "icon-192.png",
    "icon-512.png",
)
GENERATED_FILES = (
    "notes.html",
    "color-notes.html",
    "questions.js",
    "home-data.js",
    "build-meta.js",
)


def safe_recreate(output):
    output = output.resolve()
    if output == ROOT or ROOT not in output.parents:
        raise ValueError(f"发布目录必须位于仓库内且不能是仓库根目录：{output}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    return output


def copy_runtime_sources(output):
    for rel in STATIC_FILES:
        source = ROOT / rel
        if not source.is_file():
            raise FileNotFoundError(f"缺少运行源文件：{rel}")
        shutil.copy2(source, output / rel)
    shutil.copytree(ROOT / "media", output / "media")


def generate_question_bundle(output):
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    text = "window.QUESTIONS=" + json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (output / "questions.js").write_text(text, encoding="utf-8", newline="\n")


def generate_notes(output):
    for _, config in build_notes.PAGE_CONFIGS.items():
        courses = build_notes.load_courses(config["index"])
        html = build_notes.render_html(courses, config)
        (output / config["html"].name).write_text(html, encoding="utf-8", newline="\n")


def generate_derived_assets(output):
    (output / "home-data.js").write_text(build_home_data.render(), encoding="utf-8", newline="\n")
    (output / "build-meta.js").write_text(
        build_release.render(output, ROOT / "questions.json"),
        encoding="utf-8",
        newline="\n",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")


def validate_local_references(output):
    errors = []
    for name in (*STATIC_FILES, *GENERATED_FILES, ".nojekyll"):
        if not (output / name).is_file():
            errors.append(f"缺少发布文件：{name}")

    for html_path in output.glob("*.html"):
        text = html_path.read_text(encoding="utf-8")
        for rel in re.findall(r'(?:src|href)="\./([^"#?]+)', text):
            if rel.startswith(("http://", "https://")):
                continue
            if not (output / rel).exists():
                errors.append(f"{html_path.name} 引用了不存在的文件：{rel}")

    sw_text = (output / "sw.js").read_text(encoding="utf-8")
    for rel in re.findall(r'"\./([^"?]*)"', sw_text):
        target = output / (rel or "index.html")
        if not target.exists():
            errors.append(f"sw.js 缓存了不存在的文件：{rel or './'}")

    if errors:
        raise ValueError("\n".join(errors))


def main():
    parser = argparse.ArgumentParser(description="生成仅含线上运行资源的 GitHub Pages Artifact")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    output = safe_recreate(args.output)
    copy_runtime_sources(output)
    generate_question_bundle(output)
    generate_notes(output)
    generate_derived_assets(output)
    validate_local_references(output)

    files = [path for path in output.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    print(f"Pages Artifact：{len(files)} 个文件，{total / 1024 / 1024:.2f} MB -> {output}")


if __name__ == "__main__":
    main()
