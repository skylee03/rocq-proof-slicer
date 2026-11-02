From Stdlib Require Import Arith.PeanoNat.

Inductive color : Type :=
| Red : color
| Green : color
| Blue : color.

Definition unused_color : color := Green.
Definition favorite : color := Red.

Lemma favorite_red : favorite = Red.
Proof.
  reflexivity.
Qed.

Theorem target : favorite = Red.
Proof.
  apply favorite_red.
Qed.
