"""Generate one deterministic build id for the quiz, lecture, color notes and PWA cache."""

from pathlib import Path
import argparse
import hashlib
import json
import sys


ROOT = Path(__file__).resolve().parents[1]


CORE_HASHED_ASSETS = [
    "app.js",
    "icon-192.png",
    "icon-512.png",
    "icon.svg",
    "home.js",
    "index.html",
    "manifest.webmanifest",
    "notes.html",
    "quiz.html",
    "color-notes.html",
    "question-media.js",
    "questions.js",
    "style.css",
    "sw.js",
]


def hashed_assets(asset_root):
    media_root = asset_root / "media"
    media = sorted(
        path.relative_to(asset_root).as_posix()
        for path in media_root.rglob("*")
        if path.is_file()
    ) if media_root.is_dir() else []
    return CORE_HASHED_ASSETS + media


def render(asset_root=ROOT, question_file=None):
    asset_root = Path(asset_root).resolve()
    question_file = Path(question_file or ROOT / "questions.json").resolve()
    digest = hashlib.sha256()
    for rel in hashed_assets(asset_root):
        path = asset_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"缺少发布资源：{rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        data = path.read_bytes()
        if path.suffix.lower() != ".png":
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
        digest.update(b"\0")
    questions = json.loads(question_file.read_text(encoding="utf-8"))
    build_id = digest.hexdigest()[:16]
    payload = {"id": build_id, "questionCount": len(questions)}
    return "globalThis.SHAOYANG_BUILD=Object.freeze(" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ");\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--asset-root", type=Path, default=ROOT / "dist")
    parser.add_argument("--question-file", type=Path, default=ROOT / "questions.json")
    args = parser.parse_args()
    asset_root = args.asset_root.resolve()
    output = asset_root / "build-meta.js"
    expected = render(asset_root, args.question_file)
    if args.check:
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if current != expected:
            print("build-meta.js 与当前发布资源不同步", file=sys.stderr)
            raise SystemExit(1)
        print("build-meta.js 已与发布资源同步")
        return
    output.write_text(expected, encoding="utf-8", newline="\n")
    print(json.loads(expected.removeprefix("globalThis.SHAOYANG_BUILD=Object.freeze(").removesuffix(");\n"))["id"])


if __name__ == "__main__":
    main()
