# Design notes

This document explains how the prototype maps the paper's ideas to a small,
practical tool.

## Mapping to the paper

| Paper concept | Prototype |
|---|---|
| program \(P\) | a `.v` file and its top-level declarations |
| target element \(E\) | a theorem/lemma/definition name |
| typechecker \(T\) | `coqc` (Rocq/Coq kernel and elaborator) |
| type rule dependency map \(M_T\) | `.glob` references (fallback: identifier occurrence) |
| signature | declaration statement/type |
| body | proof script or definition body |
| exact slice | keep all reachable declarations and proofs |
| approximate slice | keep auxiliary statements, `Admit` their proofs |

## Algorithm

1. **Parse** the source into a preamble and top-level declarations.
2. **Build a dependency graph**:
   - Preferred: parse Rocq's `.glob` file, which records source spans for
     references, and map references inside each declaration's span to other
     top-level declarations.
   - Fallback: collect identifier occurrences and intersect with declaration
     names. This is deliberately over-approximate.
3. **Compute the closure** from the target with a worklist:
   - exact mode follows all dependencies;
   - skeleton mode follows only statement dependencies for auxiliary lemmas.
4. **Render** the reachable declarations. In skeleton mode, an auxiliary
   lemma's proof is replaced by `Proof. Admitted.`.
5. **Validate** with `coqc` and, when needed, `Print Assumptions`.

## Why `.glob`?

A regex over identifiers conflates top-level constants with local variables
and notations. Rocq's `.glob` file distinguishes these and gives source spans,
so the dependency graph is much more precise. It is still only a *reference*
graph: it does not record which definitions are unfolded during conversion.

## Exact vs approximate

- **Exact**: all reachable proof bodies are kept. The result should be
  kernel-checkable without new axioms.
- **Approximate/skeleton**: auxiliary theorem proofs are `Admitted`. The
  result is a proof skeleton; `Print Assumptions` lists the stubs the target
  depends on.

The skeleton mode mirrors the paper's "keep the signature, drop the body"
idea. It is useful for LLM context reduction and proof repair, but it is not a
complete proof.

## Dynamic minimization

`--minimize` treats `coqc` as an oracle. It greedily tries to remove each
kept declaration and keeps the removal if the candidate still checks. This
recovers precision when the static map over-approximates (see
`corpus/false_positive.v` with `--no-glob`).

## Limitations

- No conversion-aware dependency analysis.
- No typeclass/`simp`/`auto` tracing.
- No tactic-level or local proof-state slicing.
- The parser is not a full Rocq parser.
- `Admitted` introduces axioms; exact mode should avoid it.

## Next steps

1. Lean 4 prototype using `Expr.getUsedConstants` and `InfoTree`.
2. Coq + MetaCoq formalization of signature slicing and preservation.
3. Better dependency extraction from proof terms and conversion traces.
