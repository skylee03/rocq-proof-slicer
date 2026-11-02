From Stdlib Require Import Arith.PeanoNat.

Definition unused_nat : nat := 41.
Definition base : nat := 2.
Definition twice : nat := base + base.

Lemma unused_add_zero : forall n : nat, n + 0 = n.
Proof.
  intros n.
  rewrite Nat.add_0_r.
  reflexivity.
Qed.

Lemma add_twice : forall n : nat, n + twice = twice + n.
Proof.
  intros n.
  apply Nat.add_comm.
Qed.

Theorem target : forall n : nat, n + twice = twice + n.
Proof.
  apply add_twice.
Qed.
