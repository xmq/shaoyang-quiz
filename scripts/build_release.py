"""Generate one deterministic build id for the quiz, lecture, color notes and PWA cache."""

from pathlib import Path
import argparse
import hashlib
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build-meta.js"
CORE_HASHED_ASSETS = [
    "app.js",
    "icon-192.png",
    "icon-512.png",
    "icon.svg",
    "home-data.js",
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
NOTE_MEDIA_PATTERNS = ("ee_*.svg", "analog_*.svg", "digital_*.svg", "comm_*.svg")
NOTE_MEDIA = sorted(
    path.relative_to(ROOT).as_posix()
    for pattern in NOTE_MEDIA_PATTERNS
    for path in (ROOT / "media").glob(pattern)
)
HASHED_ASSETS = CORE_HASHED_ASSETS + NOTE_MEDIA


def render():
    digest = hashlib.sha256()
    for rel in HASHED_ASSETS:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"缺少发布资源：{rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        data = path.read_bytes()
        if path.suffix.lower() != ".png":
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
        digest.update(b"\0")
    questions = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    build_id = digest.hexdigest()[:16]
    payload = {"id": build_id, "questionCount": len(questions)}
    return "globalThis.SHAOYANG_BUILD=Object.freeze(" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ");\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != expected:
            print("build-meta.js 与当前发布资源不同步", file=sys.stderr)
            raise SystemExit(1)
        print("build-meta.js 已与发布资源同步")
        return
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(json.loads(expected.removeprefix("globalThis.SHAOYANG_BUILD=Object.freeze(").removesuffix(");\n"))["id"])


if __name__ == "__main__":
    main()
