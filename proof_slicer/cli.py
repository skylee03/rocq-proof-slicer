"""Command-line interface for the Rocq proof slicer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .slicer import build_slice, write_dot, write_mermaid


def main() -> None:
    ap = argparse.ArgumentParser(description="Declaration-level proof slicing for Rocq/Coq.")
    ap.add_argument("input", type=Path)
    ap.add_argument("target")
    ap.add_argument("-o", "--output", type=Path, default=Path("sliced.v"))
    ap.add_argument("--stub-aux", action="store_true", help="keep auxiliary statements, Admit their proofs")
    ap.add_argument("--minimize", action="store_true", help="use the Rocq compiler as an oracle to remove more declarations")
    ap.add_argument("--dot", type=Path, help="write a Graphviz .dot dependency graph")
    ap.add_argument("--mermaid", type=Path, help="write a Mermaid dependency graph")
    ap.add_argument("--refresh-glob", action="store_true", help="re-run the compiler even if .glob looks fresh")
    ap.add_argument("--no-glob", action="store_true", help="use the identifier heuristic instead of .glob")
    ap.add_argument("--json", action="store_true", help="print a JSON summary instead of text")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--timeout", type=int, default=120, help="compiler timeout in seconds")
    args = ap.parse_args()

    result = build_slice(
        args.input,
        args.target,
        stub_aux=args.stub_aux,
        minimize=args.minimize,
        force_glob=args.refresh_glob,
        use_glob=not args.no_glob,
        verbose=not args.quiet,
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result["text"])
    if args.dot:
        write_dot(args.dot, result["blocks"], result["keep"], args.target, args.stub_aux)
    if args.mermaid:
        write_mermaid(args.mermaid, result["blocks"], result["keep"], args.target, args.stub_aux)

    summary = {
        "input": result["input"],
        "target": result["target"],
        "dep_source": result["dep_source"],
        "total_decls": result["total_decls"],
        "keep_decls": result["keep_decls"],
        "dropped": result["dropped"],
        "original_lines": result["original_lines"],
        "sliced_lines": result["sliced_lines"],
        "minimize": result["minimize"],
        "output": str(args.output),
        "dot": str(args.dot) if args.dot else None,
        "mermaid": str(args.mermaid) if args.mermaid else None,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if args.quiet:
        return

    print(f"target: {result['target']}")
    print(f"deps:   {result['dep_source']}")
    print(f"kept:   {result['keep_decls']} / {result['total_decls']} declarations")
    print(f"lines:  {result['original_lines']} -> {result['sliced_lines']}")
    print(f"dropped: {', '.join(result['dropped']) if result['dropped'] else '(none)'}")
    if result["minimize"]:
        ms = result["minimize"]
        print(f"minimize: {ms['attempts']} attempts, removed {len(ms['removed'])}, {ms['seconds']}s")
    print(f"wrote:  {args.output}")
    if args.dot:
        print(f"dot:    {args.dot}")
    if args.mermaid:
        print(f"mermaid:{args.mermaid}")
