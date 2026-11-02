From Stdlib Require Import Arith.PeanoNat.

Record point := {
  px : nat;
  py : nat
}.

Definition origin : point := {| px := 0; py := 0 |}.
Definition unused_point : point := {| px := 1; py := 1 |}.

Lemma origin_px : px origin = 0.
Proof.
  reflexivity.
Qed.

Theorem target : px origin = 0.
Proof.
  apply origin_px.
Qed.
