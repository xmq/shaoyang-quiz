"""Render the maintained SVG into standard and adaptive PWA icons."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main(browser_path):
    svg = (ROOT / "icon.svg").read_text(encoding="utf-8")
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    document = ET.fromstring(svg)
    background = document.find("{http://www.w3.org/2000/svg}rect")
    background.set("rx", "0")
    adaptive = ET.tostring(document, encoding="unicode")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=browser_path, headless=True)
        for size, filename, source in (
            (192, "icon-192.png", svg),
            (512, "icon-512.png", svg),
            (512, "icon-maskable-512.png", adaptive),
        ):
            page = browser.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
            page.set_content(f'<style>html,body{{margin:0;width:100%;height:100%;background:transparent}}svg{{display:block;width:100%;height:100%}}</style>{source}')
            page.screenshot(path=str(ROOT / filename), omit_background=True)
            page.close()
            print(filename, size)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-path", default="C:/Program Files/Google/Chrome/Application/chrome.exe")
    main(parser.parse_args().browser_path)
