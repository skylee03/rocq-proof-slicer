#!/usr/bin/env python3
"""Regression checks for the Rocq proof-slicer prototype."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def main() -> None:
    # 0. toolchain
    proc = run(["coqc", "--version"], check=True)
    assert_in("Rocq", proc.stdout + proc.stderr, "Rocq toolchain")

    # 1. original compiles
    run(["coqc", "-q", "demo.v"], check=True)

    # 2. exact slice
    proc = run(["python3", "slice.py", "demo.v", "target", "-o", "sliced.v"], check=True)
    assert_in("kept:   5 / 8", proc.stdout, "exact slice count")
    assert_in("dropped: unused1, unused_lemma, unused_lemma2", proc.stdout, "exact slice drops")
    run(["coqc", "-q", "sliced.v"], check=True)

    # 3. skeleton
    proc = run(
        ["python3", "slice.py", "demo.v", "target", "--stub-aux", "-o", "sliced_stub.v"],
        check=True,
    )
    assert_in("kept:   4 / 8", proc.stdout, "skeleton count")
    assert_in("dropped: helper", proc.stdout, "skeleton drops helper")
    proc = run(["coqc", "-q", "sliced_stub.v"], check=True)
    assert_in("Axioms:", proc.stdout + proc.stderr, "skeleton assumptions")
    assert_in("used_lemma", proc.stdout + proc.stderr, "skeleton lists used_lemma")

    # 4. over-approximation + dynamic minimization
    run(["coqc", "-q", "corpus/false_positive.v"], check=True)
    proc = run(
        [
            "python3", "slice.py", "corpus/false_positive.v", "target",
            "--no-glob", "--minimize", "-o", "sliced_min.v",
        ],
        check=True,
    )
    assert_in("removed 1", proc.stdout, "minimize removed one")
    assert_in("kept:   2 / 3", proc.stdout, "minimize final count")
    run(["coqc", "-q", "sliced_min.v"], check=True)

    # 5. error localization
    proc = run(["coqc", "-q", "broken.v"])
    assert proc.returncode != 0, "broken.v should fail"
    run(["python3", "slice.py", "broken.v", "broken", "-o", "broken_sliced.v"], check=True)
    proc = run(["coqc", "-q", "broken_sliced.v"])
    assert proc.returncode != 0, "broken_sliced.v should fail"
    assert_in('Unable to unify "n" with "n + 1"', proc.stdout + proc.stderr, "same kernel error")

    # 6. batch
    proc = run(["python3", "batch.py", "corpus", "--target", "target"], check=True)
    assert_in("| ok |", proc.stdout, "batch has successful rows")
    if "check-fail" in proc.stdout or "orig-fail" in proc.stdout:
        print(proc.stdout)
        raise SystemExit("batch had a failure")

    print("all prototype tests passed")


if __name__ == "__main__":
    main()
