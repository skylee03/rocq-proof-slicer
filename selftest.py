#!/usr/bin/env python3
"""End-to-end regression checks for the Rocq proof-slicer prototype."""
from __future__ import annotations

import subprocess
from pathlib import Path

from proof_slicer.slicer import compiler_command, run_coqc

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return proc


def assert_in(needle: str, haystack: str, label: str) -> None:
    if needle not in haystack:
        print(f"FAIL: {label}: expected {needle!r} in output")
        print(haystack)
        raise SystemExit(1)


def compile_file(relative: str, should_succeed: bool = True) -> str:
    path = ROOT / relative
    ok, output = run_coqc(path, cwd=path.parent)
    if ok != should_succeed:
        print(f"FAIL: unexpected compile result for {relative}")
        print(output)
        raise SystemExit(1)
    return output


def main() -> None:
    # 0. toolchain: coqc (coq-core compatibility package) or rocq compile
    proc = run(compiler_command() + ["--version"], check=True)
    assert_in("Rocq", proc.stdout + proc.stderr, "Rocq toolchain")

    # 1. original compiles
    compile_file("demo.v")

    # 2. exact slice
    proc = run(["python3", "slice.py", "demo.v", "target", "-o", "sliced.v"], check=True)
    assert_in("kept:   5 / 8", proc.stdout, "exact slice count")
    assert_in("dropped: unused1, unused_lemma, unused_lemma2", proc.stdout, "exact slice drops")
    compile_file("sliced.v")

    # 3. skeleton
    proc = run(
        ["python3", "slice.py", "demo.v", "target", "--stub-aux", "-o", "sliced_stub.v"],
        check=True,
    )
    assert_in("kept:   4 / 8", proc.stdout, "skeleton count")
    assert_in("dropped: helper", proc.stdout, "skeleton drops helper")
    output = compile_file("sliced_stub.v")
    assert_in("Axioms:", output, "skeleton assumptions")
    assert_in("used_lemma", output, "skeleton lists used_lemma")

    # 4. over-approximation + dynamic minimization
    compile_file("corpus/false_positive.v")
    proc = run(
        [
            "python3", "slice.py", "corpus/false_positive.v", "target",
            "--no-glob", "--minimize", "-o", "sliced_min.v",
        ],
        check=True,
    )
    assert_in("removed 1", proc.stdout, "minimize removed one")
    assert_in("kept:   2 / 3", proc.stdout, "minimize final count")
    compile_file("sliced_min.v")

    # 5. error localization
    output = compile_file("broken.v", should_succeed=False)
    assert_in('Unable to unify "n" with "n + 1"', output, "original kernel error")
    run(["python3", "slice.py", "broken.v", "broken", "-o", "broken_sliced.v"], check=True)
    output = compile_file("broken_sliced.v", should_succeed=False)
    assert_in('Unable to unify "n" with "n + 1"', output, "same kernel error")

    # 6. batch
    proc = run(["python3", "batch.py", "corpus", "--target", "target"], check=True)
    assert_in("| ok |", proc.stdout, "batch has successful rows")
    if "check-fail" in proc.stdout or "orig-fail" in proc.stdout:
        print(proc.stdout)
        raise SystemExit("batch had a failure")

    print("all prototype tests passed")


if __name__ == "__main__":
    main()
