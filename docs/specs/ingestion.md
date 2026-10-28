# Spec: Corpus ingestion — Laws of the Game 2026/27

Status: decisions resolved (§10), ready to build M1 · Build plan: [docs/plans/m1-build-plan.md](../plans/m1-build-plan.md) · Owner: Jete · Source file: `data/raw/Laws of the Game 2026_27_single pages.pdf`

This spec is grounded in read-only `pymupdf` probes of the actual PDF (Oct 2026). Every rule below cites the pages it was derived from, so you can open the PDF and check. It deliberately quotes headings only, not Law text, so it is safe to commit.

---

## 1. Goal and scope

Turn the 2026/27 English single-page PDF into one JSONL file of clause records with stable, deterministic IDs, plus an ingest report. Retrieval, citations and the gold set all key off `clause_id`.

Build it in four increments. Each one is shippable on its own, and the Week 1 acceptance criteria only require M1.

| Increment | Content | Pages | doc_type |
| --- | --- | --- | --- |
| **M1** | Laws 1–17 | 44–151 | `law` |
| **M2** | VAR protocol, front matter ("About the Laws", "Notes and modifications"), glossary | 152–161, 9–42, 194–207 | `var_protocol`, `front_matter`, `glossary` |
| **M3** | Law changes (outline, details, editorial) | 166–193 | `law_change` |
| **M4** *(deferred, not v1; §10)* | Practical guidelines for match officials, FIFA Quality Programme | 208–239, 162–165 | `practical_guidelines`, `other` |

Skip entirely: covers and blanks (p1–3, 5, 8), the legal notice (p4), the contents (p6–7) and the blank "Notes" pages (p240–260). The TOC is still useful as a **check**; see §8.

---

## 2. What the PDF actually looks like

### 2.1 Basics

- 260 pages, A5 portrait (419.5 × 595.3 pt), InDesign export, **no embedded outline** (`doc.get_toc()` is empty). Structure must come from typography.
- **Printed page number = PDF page index + 1**, so `page` can simply be `index + 1`. Spot-checked on p45, p115 and p196.
- The layout is single-column apart from diagrams, the Law 14 summary table (p138–139) and the practical-guidelines diagrams.

### 2.2 Page map (from divider pages and page titles)

Each Law has a **divider page**: an image with "Law" in Roag-UltraLight 45 and a huge numeral in Roag-UltraLight 232. The Law's text starts on the next page, which opens with the Law title in Roag-UltraLight 33.

| Law | Divider | Text pages | | Law | Divider | Text pages |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 44 | 45–53 | | 10 | 102 | 103–107 |
| 2 | 54 | 55–57 | | 11 | 108 | 109–113 |
| 3 | 58 | 59–65 | | 12 | 114 | 115–129 |
| 4 | 66 | 67–71 | | 13 | 130 | 131–133 |
| 5 | 72 | 73–83 | | 14 | 134 | 135–139 |
| 6 | 84 | 85–91 | | 15 | 140 | 141–143 |
| 7 | 92 | 93–95 | | 16 | 144 | 145–147 |
| 8 | 96 | 97–99 | | 17 | 148 | 149–151 |
| 9 | 100 | 101 | | VAR | 152 | 153–161 |

Don't hard-code this table in the parser; detect it. Use it as a test fixture.

### 2.3 Typography → role

All "ink" is colour `#467082` unless noted. Sizes vary slightly (9.0 / 9.2 / 8.9 can appear **within one paragraph**, e.g. p116), so bucket sizes (8.7–9.4 ≈ "9") and key mainly on **font family + colour**.

| Font (size) | Role | Examples |
| --- | --- | --- |
| `Cambria` (≈9) | Body text | ~194k chars, the bulk of the book |
| `Cambria-Bold` (≈9) `#467082` | Inline emphasis inside body: **keep as text** | p24 |
| `Cambria-Bold` (≈9) `#94c7d6` (light blue), whole line | **Minor heading (H3)**, in the Laws as well as front matter. 14 occurrences in p9–161. If it ends in `:`, it's a lead-in instead (see §5.3) | p24–25, p105–107, p120, p125, p136, p138; also the "refer to graphics" notes on p78 and p88 |
| `Cambria-Italic` (≈9), starts with `*` | Footnote | p20, p24, p59 |
| `Cambria` (5.2) | Superscript ordinal ("1st", "3rd"): join with no space | p20, p36 |
| `Roag-ExtraBold` (≈9), matches `^\d+\.` | **Section heading** ("1. Direct free kick") | every Law |
| `Roag-ExtraBold` (8.5), matches `^[a-e]\.` | VAR protocol lettered item | p153, p155 |
| `Roag-Bold` (≈9) | **Subheading** ("Handling the ball") | p116, p121–127 |
| `Roag-ExtraBold` (≈9), no number | Glossary term; Law-changes entry header | p196; p170+ |
| `Roag-Light` (≈9), text is just `•` | Nested-bullet glyph | p116, p125 |
| `Roag-UltraLight` (33) | Page title = unit title (can wrap to 2–3 lines) | p45, p115 |
| `Roag-UltraLight` (45/50/232) | Divider pages | p44, p114 |
| `Roag-Black` / `Roag-Regular` (6.0), y ≥ 560 | **Running footer** + page number | every page |
| Any Roag at 5.5 / 7.0 / 7.8 / 14, white `#ffffff` or yellow `#e0e558`, or vertical text (`dir != (1,0)`) | Diagram / figure labels: **drop** | p46, p48, p51, p211 |
| `Roag-Black` (≈9) on signal pages | Signal captions: **drop** in v1 | p78–81, p88–91 |
| `Roag-Light` (20) | Glossary letter dividers ("A", "K"): **drop** | p196–205 |

### 2.4 Noise to strip

- **Running footer, not header.** It sits at baseline y ≈ 570. Odd pages have `Laws of the Game 2026/27  |  Law 12  |  Fouls and Misconduct` plus the page number at x ≈ 373. Even pages have only the page number, at x ≈ 40. Rule: drop every span whose baseline y > 555. Nothing at the top of the page repeats.
- **`\x07` (BEL) control characters**: 922 in the document, at paragraph starts and after bullet markers (an InDesign artifact). Strip all of them.
- **Bullet markers**: `•` + U+2002 (en space), 843 of them. Normalize to a single representation of your choice, but keep list structure (see §5).
- Tabs inside section headings (`10.\tGoals`), NBSP (4) and thin space (3) → plain space.
- Curly quotes and en dashes: keep them in `text`. BM25 tokenization can normalize later.

### 2.5 Traps found in probing

1. **Block order ≠ reading order.** `get_text("dict")` returns the page-title block **last** (p45, p115). Sort lines by baseline y, then x.
2. **Cambria line bboxes are ~50 pt tall** for 9 pt text (broken font metrics; lines overlap). Never use bbox height for gap or strike detection. Use span `origin` (baseline) and `size`.
3. **Pages are not paragraphs.** A paragraph, or more often a bullet list, continues across page breaks in at least 13 places in Laws 1–17 (§5.3).
4. **Headings split across styles:**
   - Law 10 S3 (p103): the number `3.` is ExtraBold, but the title "Penalties (penalty shoot-out)" on the **same baseline** is Roag-Bold.
   - Law 12 (p124): the subheading on DOGSO is Roag-Bold, but the acronym `(DOGSO)` on the same baseline is ExtraBold.
   - VAR 2e (p155): the lettered heading wraps onto three ExtraBold lines at x ≈ 91.
5. **The Law 14 summary table** (p138–139) is a real 3-column table that spans two pages, and the second page has no header row. `page.find_tables()` was tested: it fragments cells and **drops spaces** ("Outcomeofthepenaltykick"). Don't use it.
6. **The Law-changes pages use strikethrough for deleted wording** and underlines for added wording. Plain extraction interleaves old and new text ("a maximum of six eight may be used"). See §6.3.
7. **Yellow underlines in the main Laws.** The main Law pages also carry yellow (`#e0e558`) underlines under text that changed this edition (e.g. p60–63, p73–78, p98, p106, p120–124). That's free metadata (§4, `changed_this_edition`).
8. **Diagram numbers look like section headings.** On p46 and p51, dimension labels such as `7.32` and `9.15` use Roag-ExtraBold and match `^\d+\.`. They differ in size (5.5 / 7 / 14 pt, never ≈9), and some are vertical or white/yellow. Drop figure labels **before** testing for section headings (the §5.2 order), and require size bucket ≈ 9 for a section heading. Apply the figure-label drop rule to Roag fonts only: Cambria 5.2 superscripts are body text.
9. **Section-heading spellings vary.** Examples: `"5.\t"` followed by a separate title span (p48); `"4. \t Reserve assistant referee"` (p87); `"14. Video…"` with no tab (p53); `"10.\tGoals"` (p50). Merge the line's spans first, then parse the joined text with `^(\d+)\.\s*(.*)`.

---

## 3. Decisions (and pushback on CLAUDE.md)

### 3.1 The CLAUDE.md example ID is wrong for this edition

CLAUDE.md uses `L12/S3` = "Disciplinary action". In 2026/27, **Law 12 has five sections**: 1 Direct free kick, 2 Indirect free kick, **3 Corner kick (new)**, **4 Disciplinary action**, 5 Restart of play after fouls and misconduct (p115–127). The editorial-changes page (p188) confirms the renumbering: it shows a cross-reference changed from 12.3 to 12.4.

Consequences:
- Section numbers are **edition-specific**. When 2025/26 is added, align editions via section *titles*, never numbers. Note this in the edition-handling ADR.
- Update the CLAUDE.md example to `2026-27/L12/S4/...`.

### 3.2 `clause_id` scheme

```
{edition}/{unit}/S{section}/{sub}/P{k}
```

| Part | Rule |
| --- | --- |
| `edition` | `2026-27` |
| `unit` | `L1`…`L17` (no zero padding; matches IFAB's own "Law 12.4" citation style, used on p32 and p36) · `VAR` · `FM-{doc}` · `PG-{doc}` · `GL` · `LC` |
| `S{section}` | The printed section number. `S0` for text before the first numbered section (Law 6 p85, Law 12 p115, Law 14 p135 and Law 17 p149 all have a preamble). Derive S0 from "body text before the first section heading"; don't hard-code which Laws have one. For unnumbered docs (front matter, PG), always `S0` |
| `{sub}` | Slug of the current subheading, or `main` before the first subheading in that section. VAR lettered items use the letter (`a`…`e`) |
| `P{k}` | 1-based ordinal of the clause within (unit, section, sub) |

Examples: `2026-27/L12/S1/main/P3`, `2026-27/L12/S1/handling-ball/P2`, `2026-27/L12/S4/dogso/P1`, `2026-27/VAR/S2/b/P1`, `2026-27/FM-sin-bins/S0/referees-signal/P1`.

**Slug rule** (must be a pure function of the heading text):
1. If the heading ends in a parenthesized all-caps acronym, the slug is that acronym, lowercased (`dogso`).
2. Otherwise: ASCII-fold, lowercase, strip punctuation, drop stopwords {a, an, the, of, and, or, to, for, in, on, with, by, from}, keep the first 5 remaining tokens, and join them with `-`.
3. On a collision within the same (unit, section), append `-2`, `-3` in reading order.

**Why not plain ordinals (`S4/C17`)?** Law 12 S4 runs eight pages with about 12 subheadings. With section-wide ordinals, any change to a merge rule while you iterate on the parser renumbers every later clause in the section, and silently breaks gold labels you've already written. Subsection-scoped ordinals limit that damage to one subheading. The IDs also read better when you label by hand.

**Freeze rule.** Once the first gold incidents are labeled, every parser run must diff its IDs against the previous snapshot (§7, AC-4). Any removed ID, or any ID whose text hash changed, is a reported break.

### 3.3 Clause = one paragraph, with its list absorbed

- A clause is one body paragraph.
- A paragraph that **ends with `:`** absorbs the bullet list that follows it, including nested bullets, into the same clause.
- A free-standing bullet list with no lead-in is one clause.
- A footnote (`*…`, italic) is appended to the clause that contains the matching `*` marker, as a separate line.

Known weakness: some absorbed lists are long (the list of cautions for unsporting behaviour in Law 12 S4 is the obvious one). **Don't split them in v1.** Log the token-length distribution (§7) and let the chunk-granularity ADR decide whether to split long lists into item-level clauses with the lead-in carried as context. That's also a natural ablation.

### 3.4 doc_type values

CLAUDE.md lists four values. The PDF needs these:

`law` · `var_protocol` · `front_matter` · `law_change` · `glossary` · `practical_guidelines` · `other` · (`circular`, later)

Rationale: the VAR protocol is binding and central to reviewability, so give it its own type for filtering instead of forcing it under `law` with a fake law number. The glossary is directly useful for the vocabulary-gap problem. `other` holds the FIFA Quality Programme, which you'll probably exclude from the default index.

---

## 4. Record schema

One JSON object per line. Keys sorted, UTF-8, `ensure_ascii=False`.

| Field | Type | Notes |
| --- | --- | --- |
| `clause_id` | str | §3.2 |
| `edition` | str | `2026-27` |
| `doc_type` | str | §3.4 |
| `unit` | str | `L12`, `VAR`, `FM-sin-bins`, `GL`, `LC`… |
| `law_number` | int \| null | 1–17 for `law`; target Law for `law_change`; else null |
| `unit_title` | str | From the page title, e.g. "Fouls and Misconduct" (replaces `law_title`, or keep both) |
| `section_number` | int \| null | Printed number; 0 for preamble |
| `section_title` | str \| null | |
| `subsection_title` | str \| null | Subheading text as printed; for front-matter H3s, `"Procedure › Requirement to leave…"` |
| `para_index` | int | The `k` in `P{k}` |
| `text` | str | Cleaned clause text; list items on their own lines |
| `context_header` | str | `"Law 12 – Fouls and Misconduct › 4. Disciplinary action › Denying a goal…"` (only the levels that exist) |
| `page` | int | First source page (CLAUDE.md compatibility) |
| `pages` | list[int] | All source pages; length > 1 when stitched |
| `is_list` | bool | Clause contains bullet items |
| `changed_this_edition` | bool | **Deferred (§10).** Any word in the clause is yellow-underlined (§2.5-7). Omit from M1 output |

Extra fields for `law_change` records only: `change_type` ("Amended text", "Additional text", "Amended signal", "Additional signal"), `target_unit`, `target_section_number`, `target_pages_cited` (the "(p. 75, 76)" numbers), `new_text`, `old_text`, `explanation`, `is_editorial`.

Extra fields for `glossary` records only: `term`, `category` ("Football bodies", "Football terms", "Referee terms").

---

## 5. Pipeline (stages, not code)

### 5.1 Extract

For each page, produce a flat list of **styled lines**: baseline y, x0, the spans (text, font, size, colour, flags), and direction. Build this from `page.get_text("dict")`. Sort by (baseline y, x0). Lines that share a baseline (±1 pt) but are separate in the dict should be merged left-to-right; this is what fixes p103 and p124.

### 5.2 Classify each line

Apply §2.3 in this order: footer band → divider/page-title → figure label (drop) → section heading → VAR letter → subheading → glossary term / LC header → nested-bullet glyph → body → **unknown**.

Never drop "unknown" silently. Count unknowns per page and print them in the report. That's how you'll find the next trap.

Classify pages first:
- *divider* (contains a Roag-UltraLight ≥ 45 span) → start a new unit;
- *blank* (no non-footer text) → skip;
- *content*.

### 5.3 Assemble clauses (state machine)

Keep the state `(unit, section, sub, k)`. A heading updates the state and resets `k`. Body lines accumulate into a paragraph buffer.

Paragraph boundaries:
- pymupdf blocks are a good first cut. One block is usually one InDesign paragraph, or one whole bullet list.
- A line beginning with `\x07` or a bullet at the left margin starts a new paragraph or list item.
- Emit the buffer on any heading, on a page-title change, or at the end of a unit.

Light-blue H3 lines (§2.3) don't change `(section, sub)` and don't reset `k`. They are appended to `subsection_title` (`"Sub › H3"`, or just `"H3"` while `sub = main`) for the clauses that follow, until the next heading of any level. Exception: an H3 line ending in `:` (p136, p138) is treated as a body lead-in for rule 1, not as a heading.

Merge rules:
1. **Lead-in + list.** A paragraph ending in `:` plus the immediately following list blocks become one clause (p115 b7+b8; p116 b4+b5).
2. **Nested bullets.** A line whose first span is the Roag-Light `•` glyph, indented about 8–10 pt beyond the parent bullet, belongs to the preceding bullet item (p116, p24, p125).
3. **Across pages.** When the last body paragraph of page *n* and the first body paragraph of page *n+1* are in the same unit, with no heading between them, merge them if **either**:
   - (a) the previous paragraph doesn't end in `[.:;?!)]` **and** the next one starts lowercase. Found at p69→70, p110→111, p111→112, p120→121.
   - (b) the previous paragraph is a list (or a lead-in ending `:`) **and** the next one starts with a bullet. Found at p68→69, p74→75, p81→82, p97→98, p105→106, p115→116, p125→126, p131→132, p136→137.

   Log every merge with both page numbers. p61→62 and p93→94 look similar but are *not* merges. Check that your rule agrees.

### 5.4 Normalize text

Strip `\x07`. Normalize the bullet glyph and tabs, and map NBSP and thin space to a space. Join wrapped lines with a single space; keep a newline between list items. Collapse runs of whitespace. Join superscript ordinals with no space. Remove nothing else.

### 5.5 Assign IDs and write

Assign IDs per §3.2. Write `data/processed/2026-27/clauses.jsonl` in document order, and `data/processed/2026-27/ingest_report.json` (§7). Running twice must produce byte-identical output: no timestamps or dict-order dependence inside the JSONL.

---

## 6. Special handlers

### 6.1 Law 14 summary table (p138–139, section "3. Summary table")

Emit **one clause per table row**, with text shaped like `"{row label}. Goal scored from the kick: {cell}. No goal scored from the kick: {cell}."`, and `sub = "summary-table"`.

How:
- **Route the table zone first.** The zone runs from the "3. Summary table" heading to the end of p139. Send it to the table handler *before* line classification: row labels are Roag-Bold, so the generic classifier would read them as subheadings.
- **Columns:** take the boundaries on each page from the x0 distribution of spans. There are three clear clusters: on p138 roughly x ≈ 44 / 154 / 265; p139 is shifted to ≈ 52 / 163 / 273. Record the values you actually find.
- **Rows:** use the **0.5 pt light-blue (`#94c7d6`) horizontal rules** from `page.get_drawings()`, not row-label positions. Labels are vertically centred against multi-line cells, so their y values don't mark row edges. The rules sit at y ≈ 420 / 448 / 476 on p138 and y ≈ 84 / 202 / 295 / 336 / 390 / 418 / 447 / 475 on p139. Ignore 1.0 pt segments, which are text underlines.
- **Header:** p138 has an ExtraBold group label ("Outcome of the penalty kick") above two Roag-Bold column headers, one of which wraps to two lines (y ≈ 403 / 416). Carry the header labels over to p139, which has no header row.

This table is decision-relevant (penalty encroachment outcomes), so it's worth the effort. It's also a good "parser struggled" item for review.

### 6.2 Image-only sections

Law 5 S6 "Referee signals" (p78–81) and Law 6 S6 / S7 assistant-referee signals (p88–91) are mostly images plus captions. Emit whatever body text exists. If a section has none, put it on an explicit `IMAGE_ONLY_SECTIONS` allowlist so the coverage check (AC-1) passes knowingly, not by accident. The Law 1 diagrams (p46, p48, p51) produce only figure labels, so expect nothing from them.

### 6.3 Law changes (M3)

Each entry is a run of ExtraBold lines followed by body text:
1. `Law N – Title (p. X[, Y])` (or `Video assistant referee (VAR) protocol`)
2. the section heading (`4. Disciplinary action`)
3. the change type (`Amended text` / `Additional text` / `Amended signal` / `Additional signal`)

After that comes body text, optionally with a Roag-Bold subheading. A Roag-Bold `Explanation` line starts the explanation. The Key on p170 says main changes are underlined in yellow, and editorial changes are underlined.

**Strike / underline detection.** Use `page.get_drawings()` and keep horizontal segments (|Δy| < 0.5, width > 3 pt). For each word, using its span's baseline `b` and font size `s`:
- **Strikethrough:** line colour = text colour (≈ `#467082`), stroke ≈ 1.0, and y within `b − 0.45s … b − 0.15s`. These words go only to `old_text`.
- **Main-change underline:** colour `#e0e558`, and y within `b … b + 0.3s`. These words go only to `new_text`.
- **Editorial underline:** text colour, at baseline height. Also `new_text`, with `is_editorial = true`.
- Unmarked words go to both. Keep the `(…)` elisions as printed.

Validate on p170, where the substitutions sentence should read "eight" in `new_text` and "six" in `old_text`. A first naive probe that used a mid-height band without filtering by colour picked up about 2,000 "struck" words in p167–193, because it caught underlines too. The colour and position filters are not optional.

IDs: `2026-27/LC/S0/{target}/P{k}`, e.g. `2026-27/LC/S0/l12-s4/P1`, with `k` = the entry's ordinal for that target. Put the outline summary (p167–169) under `sub = summary-…`, or skip it; it duplicates the details. The editorial changes (p188–193) use the same entry format with `is_editorial = true`.

### 6.4 Glossary (M2)

p195–207. Each term is an ExtraBold line followed by its Cambria definition in the same block. Emit one record per term: `clause_id = 2026-27/GL/S0/{category-slug}/{term-slug}`, with `P{k}` dropped because terms are unique. Drop the Roag-Light 20 letter dividers.

---

## 7. Acceptance criteria

The CLAUDE.md criteria, made testable:

- **AC-1 Coverage.** All 17 Laws are present. Every numbered section of every Law has at least one clause, unless it's on `IMAGE_ONLY_SECTIONS`. Section numbers per Law are contiguous from 1, with no gaps or duplicates. Expected section counts (fixture `tests/fixtures/sections.json`; the contents pages list only Law titles, so this was built from the heading probe): L1 14, L2 3, L3 10, L4 6, L5 7, L6 7, L7 5, L8 2, L9 2, L10 3, L11 4, L12 5, L13 3, L14 3, L15 2, L16 2, L17 2.
- **AC-2 No noise.** A regex sweep over `text` finds zero hits for:
  - `Laws of the Game 20\d\d/\d\d`
  - `\|\s*Law \d+\s*\|`
  - `[\x00-\x08\x0b-\x1f]`
  - ` `
  - a whole-line page number `^\d{1,3}$`
  - divider remnants like `^Law\s?\d+$`
- **AC-3 Unique + deterministic.** All `clause_id`s are unique. Two consecutive runs produce byte-identical JSONL (compare hashes).
- **AC-4 Snapshot diff.** The ingest compares against the previous `clauses.jsonl`, if one exists, and reports added, removed and text-changed IDs. Once gold labeling starts, any removal is a failure you have to acknowledge.
- **AC-5 Hand check.** Check 20 random clauses plus these forced ones against the PDF:
  - p103 (L10 S3 heading)
  - p116 (nested bullets)
  - p120→121 (mid-sentence break)
  - p124 (DOGSO heading)
  - p138–139 (one table row)
  - p155 (VAR 2e)
  - p24 (front-matter H3), for M2
  - p170 (strike/underline), for M3

  Record pass/fail per clause in a small markdown checklist in `data/processed/` (it contains text, so keep it git-ignored).
- **AC-6 Report.** `ingest_report.json` and stdout show:
  - clause count per unit, with Law 12 the largest;
  - counts per doc_type;
  - a token-length histogram and the 10 longest clauses by ID;
  - every cross-page merge;
  - dropped spans per page, by reason (footer / figure / caption / unknown);
  - the allowlisted empty sections.

**Sanity band, not a target.** A rough probe counted about 410 paragraph-level units across Laws 1–17 before list-absorption tuning: L12 ≈ 73, L1 ≈ 52, L3 ≈ 44, L14 ≈ 36, L4 and L5 ≈ 33 each, L9 ≈ 5. If you land far outside, say under 250 or over 700, a merge rule is wrong.

---

## 8. Tests

- The PDF can't be committed, so tests that need it must **skip when `data/raw/…pdf` is absent**. Then the public repo stays green while your local runs are real.
- Pure-function unit tests that need no PDF: the slug rule (including the acronym rule and collisions), text normalization (BEL, bullets, superscripts), the cross-page merge predicate given two synthetic paragraphs, and strike classification given a synthetic word bbox, baseline and line.
- PDF-backed tests: the page map from §2.2 as a fixture; AC-1 to AC-3; the specific pages in AC-5 as assertions on structure (section and sub assignment, number of list items, `pages` length). Assert on structure, not on copied text.
- TOC check: parse the contents pages (p6–7) and assert every listed unit title appears as some record's `unit_title`.

---

## 9. Housekeeping before you start

- `.gitignore` currently has `data/raw` but **not `data/processed/`**. Add it before the first run.
- Add the dependency: `uv add pymupdf`. Import it as `import pymupdf`; the `fitz` name now raises a deprecation warning. The current wheel also pulled in onnxruntime and networkx transitively, so check `uv tree` and pin the version you test against.
- Suggested entry point (your call): `uv run python -m ref_do_something.ingest --pdf "data/raw/…" --edition 2026-27 --out data/processed/2026-27/`. Splitting extract / classify / assemble / ids / lawchanges into separate modules keeps the pure functions testable without the PDF.

## 10a. Alternative evaluated: Docling (2026-10-27)

Docling 2.143.1 (default `DocumentConverter`, OCR on) was run on a 12-page subset (p69, 70, 103, 115, 116, 120, 121, 124, 138, 139, 155, 170). It took 42 s and installed 103 packages, including PyTorch.

| Check | Docling result |
| --- | --- |
| Footers / page numbers | ✅ All classified as `page_footer` furniture |
| Split-style headings (p103 L10 S3, p124 DOGSO) | ✅ Merged correctly |
| Light-blue H3 lines (p120, p138) | ✅ Detected as headings. This exposed a gap in this spec, now fixed in §2.3 and §5.3 |
| Law 14 table (p138–139) | ✅ Mostly correct: right columns, spaces preserved. p138 emits each row as two visual-line rows that need merging |
| Heading levels | ❌ Every heading is `level=1`. Section vs subheading could be re-derived from text (`^\d+\.`), but subheading vs H3 can't |
| VAR 2e (p155) | ❌ The multi-line lettered heading became a list item and lost its `e.` marker |
| Nested bullets (p116) | ❌ Flattened: every item at the same depth |
| Cross-page stitching (p120→121, p115→116) | ❌ Not stitched |
| OCR on logo images | ❌ Junk text inserted ("JFAB", "1FAB°", a garbled IFAB name), once glued onto a Law sentence on p120. Turning OCR off would probably fix this; the PDF is born-digital |
| `\x07` characters | ❌ 76 left in the subset |
| Law-change strikethrough (p170) | ❌ Old and new text interleaved ("six eight") |
| Law-change entry header (p170) | ❌ Emitted as a one-column table |

**Decision: keep pymupdf as the parser.** Docling's misses (heading levels, nesting, stitching, strikethrough) are exactly what the clause IDs depend on, and its wins are mostly cheap rules here. Optional: use a Docling run as a *development-time cross-check* (compare heading sets per page), not as a runtime dependency. This comparison is also worth a paragraph in the write-up.

## 10. Decisions (resolved 2026-10-26)

1. **Clause IDs: subsection slugs** (§3.2), e.g. `2026-27/L12/S4/dogso/P1`. To be recorded in **ADR-NNN: chunk granularity and clause IDs**. Update the CLAUDE.md schema example to match.
2. **doc_type: all seven values** (§3.4). Update the CLAUDE.md corpus table and schema to match.
3. **`changed_this_edition`: deferred.** Not part of M1. Revisit when the 2025/26 edition is added.
4. **Practical guidelines: deferred.** M4 is out of v1 scope. FIFA Quality Programme (`other`) is deferred with it.
