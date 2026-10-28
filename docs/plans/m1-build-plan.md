# M1 corpus ingestion: build plan

Date: 2026-10-27 · Implements: [ingestion spec](../specs/ingestion.md), [ADR-NNN: clause IDs](../adr/ADR-NNN-chunk-granularity-and-clause-ids.md), [ADR-NNN: pymupdf over Docling](../adr/ADR-NNN-pdf-parser-pymupdf-over-docling.md)

Scope: M1 in detail (Laws 1–17, `doc_type = law`, AC-1 to AC-6), then outlines of M2 and M3. M4 and `changed_this_edition` are deferred.

Effort sizes: **S** is under an hour, **M** is about a sitting, **L** is more than one sitting.

---

## 0. Housekeeping (one sitting, S)

1. **gitignore.** Add `data/processed/` to `.gitignore`. Check with `git check-ignore -v data/processed/x.jsonl`. When you fix the CLAUDE.md ID example (`L12/S4`), also change "Windows/Anaconda" to macOS/uv.
2. **Dependencies.** Run `uv add "pymupdf==2.0.*"` and `uv add --dev pytest`. Look over `uv tree`, then commit `uv.lock`.
3. **Package layout** under `src/ref_do_something/ingest/`:

   | File | Purpose |
   | --- | --- |
   | `__main__.py` | CLI: `python -m ref_do_something.ingest --pdf … --edition 2026-27 --out data/processed/2026-27/` |
   | `models.py` | Dataclasses `Span`, `StyledLine`, `Para`, `Record` |
   | `normalize.py`, `slug.py`, `merge.py` | Pure functions; **no pymupdf import** |
   | `extract.py`, `classify.py`, `assemble.py`, `tables.py`, `ids.py`, `report.py` | Pipeline stages |
   | `dump.py` | Debug printer: `python -m ref_do_something.ingest.dump --page 116` shows y, x, font, size, colour, role and text for every line. Build it early; you'll use it daily. |

4. **Tests.**
   - Folders: `tests/unit/` (no PDF needed), `tests/pdf/` (needs the PDF), and `tests/fixtures/` for `page_map.json` and `sections.json` (headings only, so safe to commit).
   - `tests/conftest.py`: a session-scoped `pdf` fixture that calls `pytest.skip("PDF not present")` when the file is missing. Register a `pdf` marker in `[tool.pytest.ini_options]`.
   - **Done when** `uv run pytest` passes with the PDF present, and the PDF tests skip when the fixture points at a missing path.

---

## 1. M1 build steps

| # | Goal | Module / functions | In → out | Spec | Done when | Effort |
|---|---|---|---|---|---|---|
| 1 | Text normalization | `normalize.clean(s)`, `join_lines(lines)`, `join_superscript(prev, sup)` | raw → clean strings | §2.4, §5.4 | Unit tests: BEL stripped; `•` + U+2002 becomes one bullet form; tab, NBSP and thin space become a space; runs collapse; "1" + "st" joins to "1st"; curly quotes and en dashes kept | S |
| 2 | Slug rule | `slug.slugify(heading)`, `slug.dedupe(slugs)` | heading → slug | §3.2, ADR | Unit tests: "…(DOGSO)" → `dogso`; "Handling the ball" → `handling-ball`; stopwords dropped; 5-token cap; accent folding; `x`, `x-2`, `x-3` in order | S |
| 3 | Merge predicates | `merge.ends_terminal(p)`, `is_lead_in(p)`, `should_merge_across_pages(prev, nxt) -> bool` | 2 synthetic `Para`s → bool | §5.3 rules 1, 3 | Unit tests for rule (a), rule (b), and negatives (ends in `.` followed by a capital; list followed by a non-bullet) | S |
| 4 | Styled-line extraction | `extract.page_lines(page, idx) -> list[StyledLine]` | `get_text("dict")` → lines sorted by (baseline y, x0); same baseline ±1 pt merged left to right; carries `block_no` | §5.1, traps 1, 2, 4 | p45 and p115: page title is the first non-footer line; p103: the S3 number and title are one line; p124: "(DOGSO)" is on the subheading line; `page == idx+1` | M |
| 5 | Line and page classification | `classify.size_bucket`, `classify_line(line) -> Role`, `classify_page(lines) -> PageKind` | lines → roles: footer, title, figure, section, subheading, h3, bullet glyph, body, unknown | §2.3, §5.2 | Detected dividers equal `page_map.json` (44, 54, …, 148, 152); `dump` shows zero `unknown` on p44–151, or a reviewed list; the p46 and p51 diagram numbers are classified as `figure` | M |
| 6 | Unit and section parsing | `parse_page_title(lines)`, `parse_section_heading(line) -> (int, str)` | roles → unit_title and section events | §2.2, §3.2 | Matches `sections.json` per Law (§7 AC-1 of the spec); S0 preamble found for L6, L12, L14, L17 | M |
| 7 | Paragraph segmentation (within a page) | `assemble.paragraphs(lines) -> list[Para]` | body lines → paras with items and depth | §3.3, §5.3 rules 1–2 | p116: nested items are attached to their parent bullet (assert item count and depths); p115: blocks 7 and 8 form one lead-in plus list | M |
| 8 | Clause state machine | `assemble.clauses(pages) -> list[Clause]` keeping `(unit, section, sub, k)` | paras + heading events → clauses | §5.3 (H3 rule, footnotes) | p120: H3 shows in `subsection_title` and `k` isn't reset; p136 and p138: an H3 ending in ":" is treated as a lead-in; footnotes appended | L |
| 9 | Cross-page stitching | wire step 3 into step 8; `merge_log` | clauses with `pages` | §5.3 rule 3 | Merge set **exactly equals** {68→69, 69→70, 74→75, 81→82, 97→98, 105→106, 110→111, 111→112, 115→116, 120→121, 125→126, 131→132, 136→137}; 61→62 and 93→94 absent; the p120→121 clause has `pages == [120, 121]` | M |
| 10 | Law 14 summary table | `tables.law14_rows(page138, page139) -> list[Clause]` | table-zone spans + drawings → one clause per row, `sub="summary-table"` | §6.1 | Row count plausible and stable; each row's text has both column labels; one row hand-checked against p138–139 | L |
| 11 | Image-only sections | `IMAGE_ONLY_SECTIONS` constant | – | §6.2 | AC-1 passes and the report lists the allowlisted entries; fill the list from real output (candidates: L5 S6, L6 S6/S7) | S |
| 12 | IDs, records, writer | `ids.assign(clauses)`, `build_record`, `write_jsonl` | clauses → `clauses.jsonl` | §3.2, §4, §5.5 | AC-3: IDs unique; two runs give the same sha256; keys sorted; `ensure_ascii=False`; no `changed_this_edition` field | S/M |
| 13 | Noise sweep | `report.noise_hits(records)` | records → hits | AC-2 | pytest asserts zero hits for all six regexes | S |
| 14 | Report and snapshot diff | `report.build(...)`, `diff_snapshot(prev, cur)` using `text_hash` | → `ingest_report.json` + stdout | AC-4, AC-6 | Per-unit counts with L12 largest; token histogram; top 10 longest; merges; drops by reason; allowlist. Editing one record in a copy makes the diff flag it as text-changed. Total in the 250–700 band | M |
| 15 | TOC check | `parse_toc(p6, p7)` | → unit titles | §8 | All 17 Law titles appear as a `unit_title` | S |
| 16 | Hand check | `report.handcheck_md(seed=…)` | 20 random + forced (p103, p116, p120→121, p124, p138–139) → markdown in `data/processed/` | AC-5 | Every row marked pass, or fixed and re-run | S code, M review |

---

## 2. Where you're most likely to get stuck

- **Block order is not reading order** (trap 1). Page titles come out last and sometimes in the wrong order: on p85, "Match Officials" comes before "The Other", plus a stray `"\n"` span. Sort by baseline, drop empty spans, then join the title lines.
- **Diagram numbers look like section headings** (spec §2.5 trap 8). Classify figures *before* sections, and require size bucket ≈ 9. The figure-label drop rule applies to Roag fonts only, because Cambria 5.2 superscripts are body text.
- **Section-heading spellings vary** (trap 9). Parse the joined line text with `^(\d+)\.\s*(.*)`.
- **Cambria bbox heights are broken** (trap 2). Any vertical-gap logic, such as paragraph breaks or nested-bullet detection, must use the span `origin` y.
- **Size bucketing.** 8.9, 9.0 and 9.2 all appear inside one paragraph (p116). Decide role mainly by font family and colour, and compare colours as ints with a tolerance helper.
- **Light-blue H3 lines.** The whole line must be `#94c7d6` Cambria-Bold. If it ends in ":" (p136, p138), it's a lead-in. An H3 doesn't reset `k` and is cleared at the next heading of any level. **This is the most likely state-machine bug.**
- **Preambles.** Let S0 fall out of "body before the first section heading" rather than hard-coding which Laws have one (L6, L12, L14, L17).
- **Law 14 table.** Route the table zone to `tables.py` *before* classification. Use the 0.5 pt light-blue rules for row boundaries (spec §6.1).
- **Cross-page merges.** Compare the last *body* paragraph of page n (after footer and figure drops) with the first body paragraph of page n+1. A heading in between blocks the merge. Assert the exact merge set.
- **Determinism.** No set iteration, no float coordinates in the output, and a fixed RNG seed for the hand-check sample.

---

## 3. M2 outline (same architecture)

- **VAR** (p152–161, `var_protocol`, unit `VAR`)
  - `classify_line` already returns a `var_letter` role in M1 (Roag-ExtraBold 8.5, `^[a-e]\.`), but nothing uses it yet. In M2 the state machine sets `sub` to the letter.
  - Merge consecutive ExtraBold lines at the same x into one heading (VAR 2e wraps over three lines on p155).
- **Front matter** (p9–42, `front_matter`, unit `FM-{slugify(title)}`)
  - Each new page title starts a new document. Section is always S0, and Roag-Bold lines become `sub`.
  - H3 lines give `"Sub › H3"`; check on p24–25.
  - Check footnotes (p20, p24) and superscripts (p20, p36).
- **Glossary** (p195–207, `glossary`, unit `GL`)
  - An ExtraBold term plus its Cambria definition makes one record. The category comes from the page title.
  - Drop the Roag-Light 20 letter dividers.
  - IDs are `GL/S0/{cat}/{term}`, with no `P`.
- **Driver.** Dispatch by page range to doc_type; `law_number` is null for these.
- **Checks.** Extend AC-1 so the front-matter documents match the TOC, and AC-5 to cover p24 and p155.

## 4. M3 outline (Law changes, p166–193)

- **Pure function first:** `lawchanges.classify_mark(word_bbox, baseline, size, segment) -> {strike, main_ul, edit_ul, none}`, unit-tested on synthetic inputs per spec §6.3. *This can be built during M1.*
- **Inputs:** horizontal segments from `get_drawings()`, plus word boxes from `page.get_text("words")`, matched to their span baselines.
- **Entry state machine:** three ExtraBold header lines → body → `Explanation` subheading.
- **Fields:** `old_text`, `new_text`, `explanation`, `target_*`, and `is_editorial` for p188–193. IDs are `LC/S0/l12-s4/P{k}`.
- **Check:** on p170, "eight" lands in new_text and "six" in old_text. Also assert the struck-word count over p167–193 is small, not the roughly 2,000 a naive probe found.

---

## 5. Order for the first ~40 gold incidents

1. **From day 1:** write incident text and decisions with **no IDs**. These don't depend on the parser.
2. **After step 9:** attach IDs for L12 S1 and S4 (fouls, handling, cautions, DOGSO; about 18 incidents), L11 (about 6) and the restart Laws L13, L15–17 (about 4).
3. **After step 10:** attach L14 IDs (about 5, including 2 that cite table rows).
4. **After step 16 passes:** freeze the snapshot. Then add multi-Law incidents (about 4) and underspecified abstention cases (about 4).
5. **VAR reviewability citations:** leave them as `TODO-VAR` until M2. They're additions, so they don't break the freeze.
6. **After the first label:** run the snapshot diff (step 14) on every parser change.
