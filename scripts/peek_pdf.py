"""Show what pymupdf extracts from a few pages of the Laws PDF.

Usage:
    uv run python scripts/peek_pdf.py 116
    uv run python scripts/peek_pdf.py 115-117 --mode text
    uv run python scripts/peek_pdf.py 138 --mode drawings

Pages are the printed page numbers (= PDF index + 1). Modes:
    spans     one row per span: baseline y, x, font, size, colour, text (default)
    blocks    same, grouped by pymupdf block and line, in pymupdf's own order
    text      plain page.get_text("text")
    words     page.get_text("words") tuples
    drawings  horizontal line segments from page.get_drawings() (rules, underlines)
"""

import argparse
from pathlib import Path

import pymupdf

DEFAULT_PDF = Path("data/raw/Laws of the Game 2026_27_single pages.pdf")


def parse_pages(spec: str) -> list[int]:
    if "-" in spec:
        first, last = spec.split("-")
        return list(range(int(first), int(last) + 1))
    return [int(spec)]


def span_row(span: dict) -> str:
    x, y = span["origin"]
    return (
        f"y={y:6.1f} x={x:6.1f}  {span['font']:<18} {span['size']:5.2f}  "
        f"#{span['color']:06x}  {span['text']!r}"
    )


def show_spans(page: pymupdf.Page) -> None:
    spans = [
        span
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    ]
    # Reading order: sort by baseline, then x (pymupdf's block order is not reading order).
    for span in sorted(spans, key=lambda s: (round(s["origin"][1], 1), s["origin"][0])):
        print(span_row(span))


def show_blocks(page: pymupdf.Page) -> None:
    for block in page.get_text("dict")["blocks"]:
        if block["type"] == 1:
            print(f"[block {block['number']}] image bbox={tuple(round(v) for v in block['bbox'])}")
            continue
        print(f"[block {block['number']}]")
        for n, line in enumerate(block["lines"]):
            print(f"  line {n} dir={tuple(round(v, 2) for v in line['dir'])}")
            for span in line["spans"]:
                print(f"    {span_row(span)}")


def show_drawings(page: pymupdf.Page) -> None:
    for drawing in page.get_drawings():
        colour = drawing.get("color")
        hex_colour = "#%02x%02x%02x" % tuple(round(c * 255) for c in colour) if colour else "none"
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) < 0.5 and abs(p2.x - p1.x) > 3:
                print(
                    f"y={p1.y:6.1f} x={p1.x:6.1f}..{p2.x:6.1f}  "
                    f"width={drawing.get('width') or 0:.2f}  {hex_colour}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pages", help="printed page number or range, e.g. 116 or 115-117")
    parser.add_argument("--mode", choices=["spans", "blocks", "text", "words", "drawings"], default="spans")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()

    doc = pymupdf.open(args.pdf)
    for page_no in parse_pages(args.pages):
        page = doc[page_no - 1]
        print(f"\n===== page {page_no} ({args.mode}) =====")
        if args.mode == "spans":
            show_spans(page)
        elif args.mode == "blocks":
            show_blocks(page)
        elif args.mode == "text":
            print(page.get_text("text"))
        elif args.mode == "words":
            for word in page.get_text("words"):
                print(tuple(round(v, 1) if isinstance(v, float) else v for v in word))
        elif args.mode == "drawings":
            show_drawings(page)


if __name__ == "__main__":
    main()
