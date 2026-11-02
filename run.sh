#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== 0. environment =="
coqc --version | head -1

echo
echo "== 1. compile original =="
coqc -q demo.v

echo
echo "== 2. exact declaration-level slice (+ graph) =="
python3 slice.py demo.v target -o sliced.v --dot sliced.dot --mermaid sliced.mmd
coqc -q sliced.v

echo
echo "== 3. proof skeleton: keep statements, Admit auxiliary proofs =="
python3 slice.py demo.v target --stub-aux -o sliced_stub.v
coqc -q sliced_stub.v

echo
echo "== 4. over-approximate map + dynamic minimization =="
python3 slice.py corpus/false_positive.v target --no-glob --minimize -o sliced_min.v
coqc -q sliced_min.v

echo
echo "== 5. error localization =="
set +e
coqc -q broken.v > /tmp/proof_slicer_broken_orig.txt 2>&1
python3 slice.py broken.v broken -o broken_sliced.v
coqc -q broken_sliced.v > /tmp/proof_slicer_broken_sliced.txt 2>&1
set -e
echo "original error:"
tail -3 /tmp/proof_slicer_broken_orig.txt
echo "sliced error:"
tail -3 /tmp/proof_slicer_broken_sliced.txt

echo
echo "== 6. batch evaluation (exact) =="
python3 batch.py corpus --target target

echo
echo "== 6b. batch evaluation (skeleton) =="
python3 batch.py corpus --target target --stub-aux
