"""Sanity checks on the hand-built fixtures, so a typo there can't mask a parser bug."""

# Spec §7 AC-1.
EXPECTED_SECTION_COUNTS = {
    "L1": 14, "L2": 3, "L3": 10, "L4": 6, "L5": 7, "L6": 7, "L7": 5, "L8": 2, "L9": 2,
    "L10": 3, "L11": 4, "L12": 5, "L13": 3, "L14": 3, "L15": 2, "L16": 2, "L17": 2,
}


def test_section_counts_match_spec(sections):
    assert {unit: len(titles) for unit, titles in sections.items()} == EXPECTED_SECTION_COUNTS


def test_page_map_is_contiguous(page_map):
    laws = page_map["laws"]
    assert [entry["law"] for entry in laws] == list(range(1, 18))
    for entry in laws:
        assert entry["first"] == entry["divider"] + 1
        assert entry["first"] <= entry["last"]
    # Each Law's text runs up to the next divider (blank pages included).
    next_dividers = [entry["divider"] for entry in laws[1:]] + [page_map["var_divider"]]
    for entry, next_divider in zip(laws, next_dividers):
        assert entry["last"] < next_divider
