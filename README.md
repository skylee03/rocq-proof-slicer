# Rocq Proof Slicer

A small, research-oriented prototype that slices Rocq/Coq proof developments at
the declaration level, inspired by **type-directed program slicing**.

> **Status:** research prototype. This is not the Specimin implementation and
> not a sound slicer for dependent type theory. See [Limitations](#limitations).

The tool starts from a target theorem, builds a dependency graph from Rocq's
`.glob` reference table, and keeps only the declarations reachable from the
target. It can also produce a **proof skeleton**: auxiliary theorem statements
are kept, but their proofs are replaced by `Admitted`, and the target is
checked with `Print Assumptions`.

## Features

- Declaration-level slicing from a target theorem.
- `.glob`-based dependency extraction, with an over-approximate fallback.
- Exact mode and proof-skeleton mode (`--stub-aux`).
- Optional dynamic minimization using the Rocq compiler as an oracle (`--minimize`).
- Error localization: slice a failing proof while preserving the kernel error.
- DOT and Mermaid dependency graph export.
- Batch evaluation over a small corpus.
- No third-party Python dependencies.

## Requirements

- Rocq 9.x with `rocq` on `PATH` (tested with Rocq 9.3.0).
- Python 3.10+.
- Optional: Graphviz for rendering `.dot` files, or any Mermaid renderer.

The prototype invokes `rocq compile` directly.

## Quick start

No installation is required:

```bash
git clone <this-repository>
cd rocq-proof-slicer
./run.sh
```

`run.sh` compiles the original demo, produces exact and skeleton slices,
runs dynamic minimization, reproduces a failing proof, and prints batch
results.

Run the regression tests:

```bash
make unit     # Python-only unit tests, no Rocq required
make test     # end-to-end tests, requires rocq
```

## Install as a command

```bash
python3 -m pip install -e .
proof-slice demo.v target -o sliced.v
proof-slice-batch corpus --target target
```

The repository also keeps thin wrappers, so these work without installing:

```bash
python3 slice.py demo.v target -o sliced.v
python3 batch.py corpus --target target
```

## Example

`demo.v` has eight declarations. An exact slice keeps five:

```text
$ python3 slice.py demo.v target -o sliced.v
target: target
deps:   .glob (demo.glob)
kept:   5 / 8 declarations
lines:  29 -> 16
dropped: unused1, unused_lemma, unused_lemma2
wrote:  sliced.v

$ rocq compile -q sliced.v
Closed under the global context
```

In skeleton mode, `helper` also disappears: it is used only inside the proof
of `used_lemma`, and that proof is now `Admitted`.

```text
$ python3 slice.py demo.v target --stub-aux -o sliced_stub.v
target: target
deps:   .glob (demo.glob)
kept:   4 / 8 declarations
lines:  29 -> 10
dropped: helper, unused1, unused_lemma, unused_lemma2

$ rocq compile -q sliced_stub.v
Axioms:
used_lemma : forall n : nat, n + used2 = used2 + n
```

## Commands

### Exact slice

```bash
rocq compile -q demo.v
python3 slice.py demo.v target -o sliced.v
rocq compile -q sliced.v
```

### Proof skeleton

```bash
python3 slice.py demo.v target --stub-aux -o sliced_stub.v
rocq compile -q sliced_stub.v
```

`Admitted` introduces axioms; `Print Assumptions` reports them.

### Over-approximation + dynamic minimization

```bash
python3 slice.py corpus/false_positive.v target --no-glob --minimize -o sliced_min.v
rocq compile -q sliced_min.v
```

The identifier heuristic sees a local variable named `helper` and keeps the
unrelated top-level `helper` declaration. `--minimize` removes it after
checking with `rocq compile`.

### Error localization

```bash
rocq compile -q broken.v || true
python3 slice.py broken.v broken -o broken_sliced.v
rocq compile -q broken_sliced.v || true
```

Both files fail with the same kernel error while the sliced file is much
smaller.

### Dependency graphs

```bash
python3 slice.py demo.v target -o sliced.v --dot sliced.dot --mermaid sliced.mmd
```

Render `sliced.dot` with Graphviz, or paste `sliced.mmd` into a Mermaid-aware
Markdown viewer.

### Batch evaluation

```bash
python3 batch.py corpus --target target
python3 batch.py corpus --target target --stub-aux
```

The output is a Markdown table with status, declarations kept, code-line
reduction, and the axioms reported by `Print Assumptions`.

## How it works

1. Parse top-level declarations from a `.v` file.
2. Prefer Rocq's `.glob` reference table for dependencies; fall back to
   identifier occurrence.
3. Compute the reachability closure from the target declaration.
4. Keep the reachable declarations; in skeleton mode, `Admit` auxiliary
   proofs and follow only their statement dependencies.
5. Validate with the Rocq compiler; optionally minimize with the compiler as an oracle.

See [docs/DESIGN.md](docs/DESIGN.md) for details.

## Limitations

This is **not** a sound type-directed slicer for dependent type theory:

- `.glob` is a reference table, not a conversion-aware typing derivation.
- It does not model definitional equality / conversion.
- It does not trace typeclass search, `simp`, or `auto` databases.
- It does not slice tactic scripts or local proof states.
- The parser handles the included demo corpus, not all Rocq syntax.
- `Admitted` introduces axioms; exact mode should avoid it.

The next steps are a Lean 4 version using `Expr.getUsedConstants` and
`InfoTree`, and a Coq + MetaCoq formalization of signature slicing and
preservation.

## Repository layout

```text
.
├── demo.v                  # main demo
├── broken.v                # failing proof for error localization
├── slice.py                # compatibility wrapper
├── batch.py                # compatibility wrapper
├── proof_slicer/           # Python package and CLI
├── corpus/                 # small evaluation corpus
├── tests/                  # Python unit tests
├── selftest.py             # end-to-end regression checks
├── run.sh                  # one-command demo
├── docs/                   # design notes and paper reference
├── CONTRIBUTING.md
├── CITATION.cff
├── LICENSE
└── README.md
```

## Paper

This prototype is inspired by:

> Loi Ngo Duc Nguyen, Tahiatul Islam, Theron Wang, Sam Lenz, and Martin Kellogg.
> **Static Program Reduction via Type-Directed Slicing.**
> *Proceedings of the ACM on Software Engineering*, 2(ISSTA), Article ISSTA091, 2025.
> DOI: [10.1145/3728968](https://doi.org/10.1145/3728968)

See [docs/PAPER.md](docs/PAPER.md). The paper is licensed under CC BY 4.0;
the code in this repository is MIT-licensed.

## License

MIT. See [LICENSE](LICENSE).
