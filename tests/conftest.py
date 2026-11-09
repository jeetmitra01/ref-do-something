import json
import os
from pathlib import Path

import pymupdf
import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
DEFAULT_PDF = REPO / "data" / "raw" / "Laws of the Game 2026_27_single pages.pdf"

# Override with LOTG_PDF=/some/path to test against another copy (or a missing one).
PDF_PATH = Path(os.environ.get("LOTG_PDF", DEFAULT_PDF))


def pytest_collection_modifyitems(items):
    # Everything under tests/pdf/ needs the PDF; mark it so `-m "not pdf"` works.
    pdf_dir = Path(__file__).parent / "pdf"
    for item in items:
        if pdf_dir in item.path.parents:
            item.add_marker(pytest.mark.pdf)


@pytest.fixture(scope="session")
def pdf_path() -> Path:
    if not PDF_PATH.is_file():
        pytest.skip(f"PDF not present: {PDF_PATH}")
    return PDF_PATH


@pytest.fixture(scope="session")
def pdf(pdf_path):
    doc = pymupdf.open(pdf_path)
    yield doc
    doc.close()


@pytest.fixture(scope="session")
def page_map() -> dict:
    return json.loads((FIXTURES / "page_map.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sections() -> dict[str, list[str]]:
    return json.loads((FIXTURES / "sections.json").read_text(encoding="utf-8"))
