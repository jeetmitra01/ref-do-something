# ADR-NNN: Chunk granularity and clause IDs

- **Status:** Proposed
- **Date:** 2026-10-26
- **Deciders:** Jete
- **Related:** [Ingestion spec](../specs/ingestion.md) §3.2–3.3, §10

## Context

Every downstream component keys off the retrieval unit and its ID:

- the retriever indexes it;
- the generator cites it;
- the citation checker verifies it;
- the gold set labels it.

Gold labeling starts in Week 1, in parallel with parser development. So IDs have to stay stable while the parser is still changing.

Three facts from probing the 2026/27 PDF shaped this decision.

1. **The Laws have four levels, not three.** The structure is Law → numbered section → unnumbered subheading → paragraph or bullet list. For example, Law 12 S4 "Disciplinary action" runs about eight pages under roughly 12 subheadings (Cautionable offences, Sending-off offences, DOGSO, …). Paragraphs and list items carry no printed numbers.
2. **Section numbers change between editions.** Law 12 gained a new section 3 "Corner kick" in 2026/27, which pushed Disciplinary action from 12.3 to 12.4. The book's own editorial-changes page shows that cross-reference being updated. The example `L12/S3` in CLAUDE.md is therefore wrong for this edition.
3. **Paragraph boundaries are a parser decision, not a fact in the PDF.** Several rules decide what counts as one clause: merging lead-ins with their lists, attaching nested bullets, and stitching text across page breaks. Those rules will change while the parser is under development.

## Decision

### Granularity: one clause = one paragraph, with its list absorbed

- A clause is one body paragraph as laid out in the PDF.
- A paragraph ending in `:` absorbs the bullet list that follows it, nested bullets included.
- A bullet list with no lead-in is one clause.
- Footnotes (`*…`) are appended to the clause that holds the matching marker.
- Clauses never cross a section or subheading boundary. They may cross page breaks; record every source page in `pages`.
- Parent context (unit title › section › subheading) is stored in `context_header`, separate from `text`. Whether it is prepended at embedding time, at BM25 indexing time, or both is a retrieval decision, not part of this ADR.
- Long lists are **not split** in v1 (see Consequences).

### Clause ID format

```
{edition}/{unit}/S{section}/{sub}/P{k}
```

| Part | Rule |
| --- | --- |
| `edition` | e.g. `2026-27` |
| `unit` | `L1`…`L17`, `VAR`, `FM-{doc}`, `GL`, `LC` (and `PG-{doc}` when practical guidelines are added) |
| `S{section}` | The printed section number; `S0` for a preamble or for unnumbered docs |
| `sub` | A slug of the current subheading; `main` before the first one; the letter (`a`…`e`) for VAR lettered items |
| `P{k}` | 1-based ordinal within (unit, section, sub) |

Examples: `2026-27/L12/S1/main/P3`, `2026-27/L12/S1/handling-ball/P2`, `2026-27/L12/S4/dogso/P1`, `2026-27/VAR/S2/b/P1`.

**Slug rule.** The slug must be a pure function of the heading text:
1. A trailing parenthesized all-caps acronym becomes the slug, lowercased (`dogso`).
2. Otherwise: ASCII-fold, lowercase, strip punctuation, drop stopwords {a, an, the, of, and, or, to, for, in, on, with, by, from}, keep the first 5 tokens, and join them with `-`.
3. On a collision within the same (unit, section), append `-2`, `-3` in reading order.

### Stability rules

1. **IDs are scoped to an edition and never reused across editions.** A clause from 2025/26 and its 2026/27 counterpart get different IDs, even when the text is identical. Linking them across editions is a separate mapping, which belongs to the edition-handling ADR.
2. **Once the first gold incident is labeled, IDs are frozen for that edition.** Every ingest run diffs against the previous snapshot and reports added, removed and text-changed IDs. A removed or renumbered ID that the gold set references fails the run until the gold set is migrated.
3. **A parser change that alters IDs needs a migration note** listing old ID → new ID. Keep that note next to the gold set.

## Alternatives considered

| Option | Why not |
| --- | --- |
| **Section-wide ordinals** (`L12/S4/C17`, the original CLAUDE.md scheme) | Shorter, but one merge-rule change near the top of a long section renumbers every later clause. Law 12 has about 70 candidate paragraphs, most of them in S4's eight pages and 12 subheadings, so a single change could invalidate a large slice of the gold set. |
| **Content hashes** (`L12/S4/9f3a…`) | Stable under segmentation changes elsewhere, but unreadable for hand labeling. They also change on any text fix, including normalization tweaks. They could be added later as a secondary `text_hash` field for drift detection, which is how AC-4 already uses them. |
| **Page-level chunks** | Kept only as an ablation baseline (CLAUDE.md lists clause-level vs page-level). Pages split paragraphs mid-sentence in at least 13 places and mix unrelated sections, which gives poor citations. |
| **Section-level chunks** | Too coarse: Law 12 S4 would be one chunk of several thousand tokens, and citations couldn't point at the actual sanction rule. |
| **List-item-level clauses** (each bullet its own clause, lead-in carried as context) | Gives the most precise citations, but many items are fragments of one to three words (the list of direct-free-kick offences in Law 12 S1), which embed poorly alone. Deferred: see Consequences. |

## Consequences

**Positive**
- IDs are readable enough to type and check by hand during gold labeling, and they match IFAB's own "Law 12.4" citation style.
- A segmentation change renumbers clauses only within one subheading, not the whole section.
- Edition-scoped IDs make edition filtering trivial, since the edition is the ID prefix.

**Negative and risks**
- **Slugs depend on heading wording.** If IFAB rewords a subheading, the slug changes, but only in a new edition, which already gets new IDs. Within one edition this is a non-issue.
- **Long absorbed lists dilute retrieval.** The longest clauses (e.g. the list of cautions for unsporting behaviour in Law 12 S4) may rank poorly and give imprecise citations. Mitigation: the ingest report logs the token-length distribution and the 10 longest clauses. If recall@k on the gold set shows long-list misses, a follow-up ADR can introduce item-level splitting. Make that an ablation: paragraph-level vs item-level for lists over N tokens.
- **IDs vary in depth.** Units like `GL` drop `P{k}` (terms are unique), so consumers must not parse IDs by fixed position. Treat the ID as opaque and use the record's fields for structure.
- **The gold set and the corpus are coupled.** The freeze rule makes parser iteration after labeling more costly. Get M1 segmentation right (spec AC-5 hand checks) before writing a large share of gold incidents.

## Follow-ups

- Update the CLAUDE.md schema example from `2026-27/L12/S3/C2` to the new format, and fix the section mapping (Disciplinary action is S4).
- Gold set labeling guidelines should reference this ID format and the freeze rule.
- The edition-handling ADR should define the cross-edition mapping by section and subheading titles.
