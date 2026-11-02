#!/usr/bin/env python3
"""A small declaration-level proof slicer for Rocq/Coq.

This is a prototype for demonstrating the *shape* of type-directed proof
slicing. It is not a sound implementation for dependent type theory.

Key ideas:
  * Use Rocq's own .glob reference table when available, instead of guessing
    dependencies with a regex.
  * Compute the reachability closure from a target theorem (the paper's
    worklist algorithm, specialized to declarations).
  * Support an "approximate" mode that keeps auxiliary theorem statements but
    replaces their proofs with Admitted, then follows only statement
    dependencies for those theorems.
  * Optionally minimize the static slice further by using coqc as an oracle.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

DECL_KINDS = (
    "Definition", "Lemma", "Theorem", "Example", "Corollary", "Proposition",
    "Fact", "Remark", "Axiom", "Parameter", "Conjecture",
    "Inductive", "CoInductive", "Variant", "Record", "Structure", "Class",
    "Instance", "Fixpoint", "CoFixpoint", "Function",
)
LEMMA_KINDS = {
    "Lemma", "Theorem", "Example", "Corollary", "Proposition", "Fact", "Remark",
}
END_RE = re.compile(r"^\s*(Qed|Defined|Admitted|Abort)\.\s*$")
PREFIX = (
    r"(?:(?:#\[[^\]]*\]|Local|Global|Program|Polymorphic|Cumulative|"
    r"NonCumulative|Private|Export)\s+)*"
)
START_RE = re.compile(
    r"^\s*" + PREFIX + r"(" + "|".join(DECL_KINDS) + r")\s+([A-Za-z_][A-Za-z0-9_']*)"
)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")


@dataclass
class Block:
    kind: str
    name: str
    text: str
    start: int          # character offset in the original file
    end: int            # character offset, exclusive
    proof_start: int | None
    deps: set[str]
    type_deps: set[str]

    @property
    def line_count(self) -> int:
        return len(self.text.splitlines())


def strip_comments(text: str) -> str:
    """Remove (possibly nested) Coq comments."""
    out: list[str] = []
    depth = 0
    i = 0
    while i < len(text):
        if text.startswith("(*", i):
            depth += 1
            i += 2
        elif text.startswith("*)", i) and depth:
            depth -= 1
            i += 2
        elif depth:
            i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def parse_blocks(text: str) -> tuple[str, list[Block]]:
    """Split a .v file into a preamble and top-level declarations.

    This is deliberately a light-weight parser, not a full Coq parser. It
    supports the declaration forms used by the demo corpus.
    """
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    preamble: list[str] = []
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        m = START_RE.match(lines[i])
        if not m:
            if not blocks:
                preamble.append(lines[i])
            i += 1
            continue

        kind, name = m.group(1), m.group(2)
        start = i
        i += 1

        if kind in LEMMA_KINDS:
            while i < len(lines) and not END_RE.match(lines[i]):
                i += 1
            if i < len(lines):
                i += 1
        else:
            # A one-line definition must not consume the next declaration.
            if lines[start].rstrip().endswith("."):
                pass
            else:
                while i < len(lines) and not lines[i].rstrip().endswith("."):
                    i += 1
                if i < len(lines):
                    i += 1

        block_text = "".join(lines[start:i])
        proof_start = None
        if kind in LEMMA_KINDS:
            rel = block_text.find("Proof.")
            if rel >= 0:
                proof_start = offsets[start] + rel

        blocks.append(
            Block(
                kind=kind,
                name=name,
                text=block_text,
                start=offsets[start],
                end=offsets[i],
                proof_start=proof_start,
                deps=set(),
                type_deps=set(),
            )
        )

    names = {b.name for b in blocks}
    for b in blocks:
        clean = strip_comments(b.text)
        toks = set(IDENT_RE.findall(clean))
        b.deps = (toks & names) - {b.name}
        stmt = re.split(r"\bProof\.", clean, maxsplit=1)[0]
        b.type_deps = (set(IDENT_RE.findall(stmt)) & names) - {b.name}

    return "".join(preamble), blocks


# ---------------------------------------------------------------------------
# .glob-based dependency extraction
# ---------------------------------------------------------------------------

REF_RE = re.compile(r"^R(\d+):(\d+)\s+(\S+)\s+<>\s+(\S+)\s+(\S+)")
MODULE_RE = re.compile(r"^F(\S+)\s*$")


def apply_glob(blocks: list[Block], glob_path: Path) -> bool:
    """Replace the identifier heuristic with Rocq's own .glob references.

    .glob records every reference with a source span. It still does not model
    conversion, but it distinguishes top-level constants from local variables
    and notations much better than a regex.
    """
    if not glob_path.exists():
        return False

    module = None
    refs: list[tuple[int, int, str]] = []
    for line in glob_path.read_text().splitlines():
        mm = MODULE_RE.match(line)
        if mm:
            module = mm.group(1)
            continue
        rm = REF_RE.match(line)
        if not rm:
            continue
        start, _end, ref_module, name, _kind = rm.groups()
        # Local variables appear as "n:1"; notations start with "::".
        if ref_module == module and ":" not in name and not name.startswith("::"):
            refs.append((int(start), int(_end), name))

    if module is None:
        return False

    names = {b.name for b in blocks}
    for b in blocks:
        inside = [
            (s, e, n)
            for (s, e, n) in refs
            if b.start <= s < b.end and n in names and n != b.name
        ]
        b.deps = {n for (_s, _e, n) in inside}
        if b.kind in LEMMA_KINDS and b.proof_start is not None:
            b.type_deps = {n for (s, _e, n) in inside if s < b.proof_start}
        else:
            b.type_deps = set(b.deps)
    return True


# ---------------------------------------------------------------------------
# Closure and rendering
# ---------------------------------------------------------------------------

def closure(blocks: list[Block], target: str, type_only_aux: bool = False) -> set[str]:
    by_name = {b.name: b for b in blocks}
    if target not in by_name:
        available = ", ".join(b.name for b in blocks) or "(none)"
        raise SystemExit(f"target declaration not found: {target}\navailable: {available}")

    seen: set[str] = set()
    work = [target]
    while work:
        n = work.pop()
        if n in seen:
            continue
        seen.add(n)
        b = by_name[n]
        deps = (
            b.type_deps
            if (type_only_aux and n != target and b.kind in LEMMA_KINDS)
            else b.deps
        )
        work.extend(deps - seen)
    return seen


def effective_deps(b: Block, target: str, type_only_aux: bool) -> set[str]:
    if type_only_aux and b.name != target and b.kind in LEMMA_KINDS:
        return b.type_deps
    return b.deps


def render(
    preamble: str,
    blocks: list[Block],
    keep: set[str],
    target: str,
    stub_aux: bool,
    print_assumptions: bool = True,
) -> str:
    out: list[str] = [preamble]
    for b in blocks:
        if b.name not in keep:
            continue
        text = b.text
        if stub_aux and b.kind in LEMMA_KINDS and b.name != target:
            # Drop the proof script entirely; keep the statement (type).
            stmt = re.split(r"(?m)^\s*Proof\.\s*$", text, maxsplit=1)[0]
            text = stmt.rstrip() + "\nProof.\nAdmitted.\n"
        out.append(text.rstrip() + "\n\n")
    if print_assumptions:
        out.append(f"Print Assumptions {target}.\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# coqc oracle
# ---------------------------------------------------------------------------

def run_coqc(path: Path, cwd: Path | None = None, timeout: int = 120) -> tuple[bool, str]:
    cwd = cwd or path.parent
    cmd = ["coqc", "-q", path.name]
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return False, "coqc not found"
    except subprocess.TimeoutExpired:
        return False, f"coqc timed out after {timeout}s"
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def cleanup_artifacts(path: Path) -> None:
    for suffix in (".vo", ".vok", ".vos", ".glob", ".aux", ".d", ".lia.cache", ".nlia.cache"):
        path.with_suffix(suffix).unlink(missing_ok=True)
    (path.parent / ("." + path.stem + ".aux")).unlink(missing_ok=True)


def ensure_glob(input_path: Path, force: bool = False, timeout: int = 120) -> tuple[bool, str]:
    """Run coqc if the .glob is missing or stale. Returns (glob_exists, output)."""
    glob_path = input_path.with_suffix(".glob")
    fresh = (
        glob_path.exists()
        and input_path.exists()
        and glob_path.stat().st_mtime >= input_path.stat().st_mtime
    )
    if fresh and not force:
        return True, ""
    _ok, output = run_coqc(input_path, cwd=input_path.parent, timeout=timeout)
    return glob_path.exists(), output


# ---------------------------------------------------------------------------
# Static slice + optional dynamic minimization
# ---------------------------------------------------------------------------

def build_slice(
    input_path: Path,
    target: str,
    stub_aux: bool = False,
    minimize: bool = False,
    force_glob: bool = False,
    use_glob: bool = True,
    verbose: bool = True,
    timeout: int = 120,
) -> dict:
    text = input_path.read_text()
    preamble, blocks = parse_blocks(text)
    if not blocks:
        raise SystemExit(f"no declarations found in {input_path}")

    glob_output = ""
    if use_glob:
        _glob_ok, glob_output = ensure_glob(input_path, force=force_glob, timeout=timeout)
        used_glob = apply_glob(blocks, input_path.with_suffix(".glob"))
    else:
        used_glob = False
    if used_glob:
        dep_source = f".glob ({input_path.with_suffix('.glob').name})"
    else:
        dep_source = "identifier heuristic"
        if use_glob and verbose and glob_output.strip():
            print("[warn] coqc did not produce .glob; falling back to identifier heuristic")

    keep = closure(blocks, target, type_only_aux=stub_aux)
    static_keep = set(keep)
    minimize_stats = None
    if minimize:
        started = time.time()
        keep, minimize_stats = minimize_keep(
            input_path, preamble, blocks, keep, target, stub_aux, timeout=timeout, verbose=verbose
        )
        minimize_stats["seconds"] = round(time.time() - started, 2)

    sliced = render(preamble, blocks, keep, target, stub_aux)
    all_names = {b.name for b in blocks}
    dropped = sorted(all_names - keep)

    def code_lines(t: str, drop_assumptions: bool = False) -> int:
        return sum(
            1
            for line in t.splitlines()
            if line.strip() and not (drop_assumptions and line.startswith("Print Assumptions"))
        )

    return {
        "input": str(input_path),
        "target": target,
        "dep_source": dep_source,
        "blocks": blocks,
        "preamble": preamble,
        "keep": keep,
        "static_keep": static_keep,
        "dropped": dropped,
        "text": sliced,
        "total_decls": len(blocks),
        "keep_decls": len(keep),
        "original_lines": code_lines(text),
        "sliced_lines": code_lines(sliced, drop_assumptions=True),
        "minimize": minimize_stats,
        "glob_output": glob_output,
    }


def compile_candidate(
    input_path: Path,
    preamble: str,
    blocks: list[Block],
    keep: set[str],
    target: str,
    stub_aux: bool,
    timeout: int,
) -> bool:
    text = render(preamble, blocks, keep, target, stub_aux)
    fd, tmp_name = tempfile.mkstemp(
        prefix="slice_min_", suffix=".v", dir=str(input_path.parent)
    )
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(text)
        ok, _out = run_coqc(tmp, cwd=input_path.parent, timeout=timeout)
        return ok
    finally:
        cleanup_artifacts(tmp)
        tmp.unlink(missing_ok=True)


def minimize_keep(
    input_path: Path,
    preamble: str,
    blocks: list[Block],
    keep: set[str],
    target: str,
    stub_aux: bool,
    timeout: int = 120,
    verbose: bool = True,
) -> tuple[set[str], dict]:
    by_name = {b.name: b for b in blocks}
    keep = set(keep)
    attempts = 0
    removed: list[str] = []
    # Try small/leaf declarations first. A second pass catches cases where
    # removing one declaration makes another removable.
    for _round in range(3):
        changed = False
        candidates = sorted(
            keep - {target},
            key=lambda n: (len(by_name[n].deps), by_name[n].start),
        )
        for name in candidates:
            if name not in keep:
                continue
            trial = keep - {name}
            attempts += 1
            ok = compile_candidate(
                input_path, preamble, blocks, trial, target, stub_aux, timeout
            )
            if verbose:
                print(f"[minimize] drop {name}: {'ok' if ok else 'no'}")
            if ok:
                keep = trial
                removed.append(name)
                changed = True
        if not changed:
            break
    return keep, {"attempts": attempts, "removed": removed}


# ---------------------------------------------------------------------------
# Graph export
# ---------------------------------------------------------------------------

def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_dot(path: Path, blocks: list[Block], keep: set[str], target: str, stub_aux: bool) -> None:
    lines = [
        "digraph proof_slice {",
        "  rankdir=LR;",
        '  node [shape=box, fontname="Menlo,monospace", fontsize=10];',
    ]
    for b in blocks:
        if b.name == target:
            attrs = 'style="filled,bold", fillcolor="#c6f6d5", color="#2f855a"'
        elif b.name in keep:
            attrs = 'style=filled, fillcolor="#bee3f8", color="#2b6cb0"'
        else:
            attrs = 'style=dashed, color="#a0aec0", fontcolor="#718096"'
        lines.append(f'  "{_dot_escape(b.name)}" [{attrs}];')
    for b in blocks:
        if b.name not in keep:
            continue
        for dep in sorted(effective_deps(b, target, stub_aux)):
            lines.append(f'  "{_dot_escape(b.name)}" -> "{_dot_escape(dep)}";')
    lines.append("}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def write_mermaid(
    path: Path, blocks: list[Block], keep: set[str], target: str, stub_aux: bool
) -> None:
    ids = {b.name: f"n{i}" for i, b in enumerate(blocks)}
    lines = ["graph LR"]
    for b in blocks:
        nid = ids[b.name]
        if b.name == target:
            cls = "target"
        elif b.name in keep:
            cls = "kept"
        else:
            cls = "dropped"
        lines.append(f'  {nid}["{b.name}"]:::{cls}')
    for b in blocks:
        if b.name not in keep:
            continue
        for dep in sorted(effective_deps(b, target, stub_aux)):
            if dep in ids:
                lines.append(f"  {ids[b.name]} --> {ids[dep]}")
    lines += [
        "  classDef target fill:#c6f6d5,stroke:#2f855a,stroke-width:2px;",
        "  classDef kept fill:#bee3f8,stroke:#2b6cb0;",
        "  classDef dropped fill:#edf2f7,stroke:#a0aec0,stroke-dasharray:5 5,color:#718096;",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
