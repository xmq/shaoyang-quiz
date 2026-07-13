"""Generate the small question index used by the platform homepage."""

from pathlib import Path
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "questions.json"


def render():
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    fields = ("id", "subject", "type", "answer")
    index = [{key: item.get(key, "") for key in fields} for item in questions]
    return "globalThis.HOME_QUESTION_INDEX=Object.freeze(" + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ");\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "home-data.js")
    args = parser.parse_args()
    output = args.output.resolve()
    expected = render()
    if args.check:
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if current != expected:
            print("home-data.js 与 questions.json 不同步", file=sys.stderr)
            raise SystemExit(1)
        print("home-data.js 已与 questions.json 同步")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8", newline="\n")
    print(f"已生成 {output}")


if __name__ == "__main__":
    main()
