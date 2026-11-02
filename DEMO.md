# 5-minute demo script

## 0:00 — Framing

> The paper slices a program while preserving the typechecker's behavior at a
> target location. I built a small Rocq prototype of the same closure idea at
> the declaration level. It is deliberately conservative: it over-approximates
> dependencies, then validates every output with `rocq compile`.

## 1:00 — Exact slice

```bash
cd rocq-proof-slicer
rocq compile -q demo.v
python3 slice.py demo.v target -o sliced.v
rocq compile -q sliced.v
```

Expected:

```text
kept: 5 / 8 declarations
dropped: unused1, unused_lemma, unused_lemma2
Closed under the global context
```

Point: the target only needs `used1 -> used2 -> used_lemma -> target`;
unrelated declarations are removed and the result still kernel-checks.

## 2:00 — Proof skeleton

```bash
python3 slice.py demo.v target --stub-aux -o sliced_stub.v
rocq compile -q sliced_stub.v
```

Expected:

```text
kept: 4 / 8 declarations
dropped: helper, unused1, unused_lemma, unused_lemma2
Axioms:
used_lemma : ...
```

Point: `helper` is used only inside the proof of `used_lemma`. Once that proof
is `Admitted`, `helper` is no longer needed. This is the paper's "keep the
signature, drop the body" idea, with `Print Assumptions` tracking the stubs.

## 3:00 — Over-approximation + dynamic minimization

```bash
python3 slice.py corpus/false_positive.v target --no-glob --minimize -o sliced_min.v
rocq compile -q sliced_min.v
```

Expected:

```text
[minimize] drop helper: ok
kept: 2 / 3 declarations
minimize: 3 attempts, removed 1
```

Point: the identifier heuristic sees a local variable named `helper` and keeps
the unrelated top-level `helper`. `--minimize` uses the Rocq compiler as an oracle and
removes it. Static slice first, dynamic check second.

## 4:00 — Error localization

```bash
rocq compile -q broken.v || true
python3 slice.py broken.v broken -o broken_sliced.v
rocq compile -q broken_sliced.v || true
```

Expected: both files fail with

```text
Unable to unify "n" with "n + 1".
```

Point: the slice keeps the same kernel error while removing unrelated
declarations. This is useful for minimizing failed LLM proofs.

## 4:30 — Batch table

```bash
python3 batch.py corpus --target target
python3 batch.py corpus --target target --stub-aux
```

Show the Markdown table: status, declarations kept, code-line reduction, and
assumptions.

## Compiler note

All commands assume `rocq` (Rocq 9.x) is on `PATH`. The tool invokes
`rocq compile`.

## 5:00 — Limitations and next steps

- `.glob` is not conversion-aware; dependent-type conversion is future work.
- No tactic-level slicing or typeclass/simp tracing in this prototype.
- `Admitted` introduces axioms; exact mode avoids them.
- Next: Lean 4 `Expr`/`InfoTree`, or Coq + MetaCoq formalization.

## Backup plan

- Run `./run.sh` once before the meeting and keep the output.
- Record a 30-second screen capture of `./run.sh`.
- If a live command fails, show `sliced.v`, `sliced_stub.v`, `broken_sliced.v`
  and the batch table from the recording.
