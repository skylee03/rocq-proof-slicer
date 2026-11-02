# Changelog

## Unreleased

- Support `rocq compile` when `coqc` is not installed (Rocq 9.x without the
  `coq-core` compatibility package).
- `ROCQ_COMPILE` environment variable to override the compiler command.

## 0.1.0 — 2025-11-02

- Initial public prototype.
- Declaration-level slicing with `.glob`-based dependency extraction.
- Exact and proof-skeleton (`--stub-aux`) modes.
- Optional dynamic minimization with `coqc` as an oracle (`--minimize`).
- DOT and Mermaid dependency graph export.
- Batch evaluation over the included corpus.
- Unit tests and an end-to-end self-test.
