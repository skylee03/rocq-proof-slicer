"""Unit tests that do not require a Rocq/Coq installation."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from proof_slicer.batch import assumptions_summary
from proof_slicer.slicer import (
    closure,
    compiler_command,
    effective_deps,
    parse_blocks,
    render,
    write_dot,
    write_mermaid,
)

SOURCE = """\
From Stdlib Require Import Arith.PeanoNat.

Definition unused : nat := 7.
Definition a : nat := 1.
Definition b : nat := a + 1.

Lemma helper : forall n m : nat, n + m = m + n.
Proof.
  apply Nat.add_comm.
Qed.

Lemma step : forall n : nat, n + b = b + n.
Proof.
  intros n.
  apply helper.
Qed.

Theorem target : forall n : nat, n + b = b + n.
Proof.
  apply step.
Qed.
"""


class ParseAndClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preamble, self.blocks = parse_blocks(SOURCE)
        self.by_name = {b.name: b for b in self.blocks}

    def test_names(self) -> None:
        self.assertEqual(
            [b.name for b in self.blocks],
            ["unused", "a", "b", "helper", "step", "target"],
        )

    def test_heuristic_dependencies(self) -> None:
        self.assertEqual(self.by_name["b"].deps, {"a"})
        self.assertEqual(self.by_name["step"].deps, {"b", "helper"})
        self.assertEqual(self.by_name["target"].deps, {"b", "step"})

    def test_exact_closure(self) -> None:
        self.assertEqual(
            closure(self.blocks, "target"),
            {"target", "step", "helper", "b", "a"},
        )

    def test_skeleton_closure(self) -> None:
        keep = closure(self.blocks, "target", type_only_aux=True)
        self.assertIn("step", keep)
        self.assertIn("b", keep)
        self.assertNotIn("helper", keep)

    def test_effective_deps(self) -> None:
        self.assertEqual(effective_deps(self.by_name["step"], "target", True), {"b"})
        self.assertEqual(
            effective_deps(self.by_name["step"], "target", False), {"b", "helper"}
        )


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preamble, self.blocks = parse_blocks(SOURCE)
        self.by_name = {b.name: b for b in self.blocks}

    def test_exact_render_keeps_helper(self) -> None:
        keep = closure(self.blocks, "target")
        text = render(self.preamble, self.blocks, keep, "target", stub_aux=False)
        self.assertIn("Lemma helper", text)
        self.assertIn("apply helper", text)
        self.assertIn("Print Assumptions target.", text)

    def test_skeleton_render_drops_helper_proof(self) -> None:
        keep = closure(self.blocks, "target", type_only_aux=True)
        text = render(self.preamble, self.blocks, keep, "target", stub_aux=True)
        self.assertIn("Lemma step", text)
        self.assertIn("Proof.\nAdmitted.", text)
        self.assertNotIn("apply helper", text)

    def test_graphs(self) -> None:
        keep = closure(self.blocks, "target", type_only_aux=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dot = tmp_path / "graph.dot"
            mmd = tmp_path / "graph.mmd"
            write_dot(dot, self.blocks, keep, "target", True)
            write_mermaid(mmd, self.blocks, keep, "target", True)
            self.assertIn("digraph proof_slice", dot.read_text())
            self.assertIn("graph LR", mmd.read_text())
            self.assertIn("target", dot.read_text())


class CompilerTests(unittest.TestCase):
    def test_override(self) -> None:
        with patch.dict(os.environ, {"ROCQ_COMPILE": "rocq compile"}, clear=False):
            self.assertEqual(compiler_command(), ["rocq", "compile"])

    def test_prefers_coqc(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "proof_slicer.slicer.shutil.which",
            side_effect=lambda name: "/opt/bin/coqc" if name == "coqc" else "/opt/bin/rocq",
        ):
            self.assertEqual(compiler_command(), ["/opt/bin/coqc"])

    def test_falls_back_to_rocq_compile(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "proof_slicer.slicer.shutil.which",
            side_effect=lambda name: None if name == "coqc" else "/opt/bin/rocq",
        ):
            self.assertEqual(compiler_command(), ["/opt/bin/rocq", "compile"])


class BatchHelperTests(unittest.TestCase):
    def test_assumptions_summary(self) -> None:
        self.assertEqual(assumptions_summary("Closed under the global context\n"), "none")
        self.assertEqual(
            assumptions_summary("Axioms:\nstep : forall n, n = n\n"), "step"
        )


if __name__ == "__main__":
    unittest.main()
