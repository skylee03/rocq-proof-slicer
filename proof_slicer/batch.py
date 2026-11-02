#!/usr/bin/env python3
"""Batch-evaluate the declaration-level slicer on a corpus of .v files."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from .slicer import build_slice, cleanup_artifacts, run_coqc


def discover(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.v")))
        elif p.suffix == ".v":
            files.append(p)
        else:
            raise SystemExit(f"not a .v file or directory: {p}")
    # Avoid slicing our own outputs.
    skip_prefixes = ("sliced", "batch_sliced", "broken_sliced")
    return [f for f in files if f.is_file() and not f.name.startswith(".") and not f.name.startswith(skip_prefixes)]


def assumptions_summary(output: str) -> str:
    if "Closed under the global context" in output:
        return "none"
    if "Axioms:" in output:
        tail = output.split("Axioms:", 1)[1]
        names: list[str] = []
        for line in tail.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Warning:"):
                continue
            names.append(line.split(" : ")[0])
        return ", ".join(names) if names else "?"
    return "?"


def evaluate(path: Path, target: str, stub_aux: bool, minimize: bool, timeout: int) -> dict:
    orig_ok, orig_out = run_coqc(path, cwd=path.parent, timeout=timeout)
    if not orig_ok:
        return {
            "file": str(path),
            "status": "orig-fail",
            "total_decls": 0,
            "keep_decls": 0,
            "original_lines": len(path.read_text().splitlines()),
            "sliced_lines": 0,
            "reduction": 0.0,
            "assumptions": "-",
            "error": orig_out.splitlines()[-1] if orig_out.splitlines() else "compiler failed",
        }

    try:
        result = build_slice(
            path,
            target,
            stub_aux=stub_aux,
            minimize=minimize,
            force_glob=False,
            verbose=False,
            timeout=timeout,
        )
    except SystemExit as e:
        return {
            "file": str(path),
            "status": "slice-fail",
            "total_decls": 0,
            "keep_decls": 0,
            "original_lines": len(path.read_text().splitlines()),
            "sliced_lines": 0,
            "reduction": 0.0,
            "assumptions": "-",
            "error": str(e),
        }

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"batch_sliced_{path.stem}_", suffix=".v", dir=str(path.parent)
    )
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(result["text"])
        ok, out = run_coqc(tmp, cwd=path.parent, timeout=timeout)
        status = "ok" if ok else "check-fail"
        assumptions = assumptions_summary(out)
        error = "" if ok else (out.splitlines()[-1] if out.splitlines() else "compiler failed")
    finally:
        cleanup_artifacts(tmp)
        tmp.unlink(missing_ok=True)

    orig = result["original_lines"]
    sliced = result["sliced_lines"]
    reduction = 100.0 * (orig - sliced) / orig if orig else 0.0
    return {
        "file": str(path),
        "status": status,
        "total_decls": result["total_decls"],
        "keep_decls": result["keep_decls"],
        "original_lines": orig,
        "sliced_lines": sliced,
        "reduction": round(reduction, 1),
        "assumptions": assumptions,
        "error": error,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--target", default="target")
    ap.add_argument("--stub-aux", action="store_true")
    ap.add_argument("--minimize", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = [
        evaluate(f, args.target, args.stub_aux, args.minimize, args.timeout)
        for f in discover(args.paths)
    ]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    print("| file | status | decls | code lines | reduction | assumptions |")
    print("|---|---|---:|---:|---:|---|")
    for r in rows:
        decls = f"{r['keep_decls']}/{r['total_decls']}" if r["total_decls"] else "-"
        lines = f"{r['original_lines']} -> {r['sliced_lines']}" if r["sliced_lines"] else "-"
        reduction = f"{r['reduction']}%" if r["sliced_lines"] else "-"
        print(
            f"| {Path(r['file']).name} | {r['status']} | {decls} | {lines} | "
            f"{reduction} | {r['assumptions']} |"
        )
    if any(r["error"] for r in rows):
        print("\nErrors:")
        for r in rows:
            if r["error"]:
                print(f"- {Path(r['file']).name}: {r['error']}")


if __name__ == "__main__":
    main()
