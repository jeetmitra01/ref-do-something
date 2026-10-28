# ADR-NNN: PDF parser: pymupdf over Docling

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Jete
- **Related:** [Ingestion spec](../specs/ingestion.md) §10a, [ADR-NNN: Chunk granularity and clause IDs](ADR-NNN-chunk-granularity-and-clause-ids.md)

## Context

The clause ID scheme depends on four structural signals from the PDF:

- the heading level (section vs subheading vs minor heading);
- list nesting;
- paragraphs that continue across page breaks;
- strikethrough in the Law-changes pages (old vs new wording).

We compared Docling 2.143.1 (default pipeline) against the font-based pymupdf approach on 12 known-hard pages.

## Decision

Use **pymupdf** as the only runtime parser.

## Why

- **Docling misses the signals the IDs depend on.** It reported every heading as level 1, flattened nested bullets, didn't join text across page breaks, and kept struck-out text ("six eight").
- **Its wins are cheap to get with pymupdf rules.** It handled footer removal and split-style headings well, but each of those is a few lines of font or position logic.
- **Default OCR added noise.** It inserted text read from logo images into the body, once in the middle of a Law sentence.
- **Cost and determinism.** It pulls in about 100 packages including PyTorch, and took about 3.5 s per page against well under a second for the whole book with pymupdf. Its model-based output can also shift between versions, which would put frozen clause IDs at risk.

## Consequences

- We write and maintain the typography rules ourselves (spec §2–§6).
- The Law 14 summary table needs a hand-built column-splitting handler. This is the one place Docling was clearly better.
- Docling stays an optional, development-only cross-check (comparing headings page by page). It is not a project dependency.
