#!/usr/bin/env python3
"""Re-splice tracked HTML fixtures onto the current skeleton.

Extracts each fixture's TITLE, CONTENT, and controlled-slot bodies, then
re-inserts them between the same markers of the new skeleton. Fixtures whose
markers are intentionally broken (bad-closing 等、マーカー自体を検査する fixture)
are listed in KEEP_AS_IS and skipped. 骨格の固定 CSS を変更したときは、
KEEP_AS_IS のうち骨格 CSS を埋め込む6件（compatibility-valid-fragment.html 以外）にも
同じ編集をテキスト置換で適用すること（マーカー破壊や固定領域の故意相違は保存し、
固定 CSS だけを骨格と一致させる）。
"""
import sys
from pathlib import Path

MARKERS = [
    ("<!-- TITLE:BEGIN -->", "<!-- TITLE:END -->"),
    ("<!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->", "<!-- VE-CONTROLLED:COMPONENT-STYLES:END -->"),
    ("<!-- VE-CONTROLLED:CONTENT:BEGIN -->", "<!-- VE-CONTROLLED:CONTENT:END -->"),
    ("<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->", "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->"),
    ("<!-- CONTENT:BEGIN -->", "<!-- CONTENT:END -->"),
]
KEEP_AS_IS = {
    "bad-closing.html", "bad-system-closing.html", "bad-fixed-region.html", "bad-nesting.html",
    # マーカー欠落を検査する fixture と骨格を持たない断片。resplice すると内容が壊れる。
    # component-bad-fixed-region.html は固定領域3（footer）に故意相違を持ち、resplice すると消える。
    "bad-title-missing.html", "compatibility-valid-fragment.html", "component-bad-fixed-region.html",
}


def between(text, begin, end):
    if begin not in text or end not in text:
        return None
    return text.split(begin, 1)[1].split(end, 1)[0]


def splice(skeleton, fixture):
    out = skeleton
    for begin, end in MARKERS:
        body = between(fixture, begin, end)
        if body is None:
            continue
        head, rest = out.split(begin, 1)
        _, tail = rest.split(end, 1)
        out = head + begin + body + end + tail
    return out


def main():
    root = Path(__file__).resolve().parents[3]
    skeleton = (root / "assets" / "skeleton.html").read_text("utf-8")
    targets = sys.argv[1:] or [str(p) for p in (root / "scripts" / "tests").glob("*.html")]
    for path in targets:
        p = Path(path)
        if p.name in KEEP_AS_IS:
            print(f"skip {p.name}")
            continue
        p.write_text(splice(skeleton, p.read_text("utf-8")), "utf-8")
        print(f"resplice {p.name}")


if __name__ == "__main__":
    main()
