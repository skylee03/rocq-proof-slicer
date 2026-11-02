From Stdlib Require Import Arith.PeanoNat.

Definition unused : nat := 7.
Definition base : nat := 2.
Definition twice : nat := base + base.

Lemma helper : forall n m : nat, n + m = m + n.
Proof.
  apply Nat.add_comm.
Qed.

Lemma step : forall n : nat, n + twice = twice + n.
Proof.
  intros n.
  apply helper.
Qed.

Theorem target : forall n : nat, n + twice = twice + n.
Proof.
  apply step.
Qed.
