"""Raw checks of PDF facts the parser relies on (spec §2.1-2.2). No parser code involved."""

import pymupdf

FOOTER_Y = 555


def big_ultralight_pages(doc: pymupdf.Document) -> list[int]:
    """1-based pages carrying a Roag-UltraLight span of size >= 45 (divider pages)."""
    pages = []
    for idx, page in enumerate(doc):
        spans = (
            span
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
        )
        if any(s["font"] == "Roag-UltraLight" and s["size"] >= 45 and s["text"].strip() for s in spans):
            pages.append(idx + 1)
    return pages


def test_basics(pdf, page_map):
    assert pdf.page_count == page_map["page_count"]
    assert pdf.get_toc() == []
    width, height = pdf[0].rect.width, pdf[0].rect.height
    assert round(width) == 420 and round(height) == 595


def test_law_dividers_detected(pdf, page_map):
    expected = [entry["divider"] for entry in page_map["laws"]] + [page_map["var_divider"]]
    in_laws = [p for p in big_ultralight_pages(pdf) if expected[0] <= p <= expected[-1]]
    assert in_laws == expected


def test_law_titles_open_text_pages(pdf, page_map):
    # The page title (Roag-UltraLight 33, possibly wrapped) is the Law title.
    for entry in page_map["laws"]:
        page = pdf[entry["first"] - 1]
        title_spans = sorted(
            (span["origin"][1], span["origin"][0], span["text"].strip())
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            if span["font"] == "Roag-UltraLight" and round(span["size"]) == 33 and span["text"].strip()
            and span["origin"][1] < FOOTER_Y
        )
        assert " ".join(text for _, _, text in title_spans) == entry["title"], entry["law"]
