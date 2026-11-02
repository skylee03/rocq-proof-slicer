From Stdlib Require Import Arith.PeanoNat.

Definition unused1 : nat := 1.

Definition used1 : nat := 2.

Definition used2 : nat := used1 + 3.

Lemma unused_lemma : forall n : nat, n + 0 = n.
Proof.
  intros n.
  rewrite Nat.add_0_r.
  reflexivity.
Qed.

Lemma helper : forall n m : nat, n + m = m + n.
Proof.
  apply Nat.add_comm.
Qed.

Lemma used_lemma : forall n : nat, n + used2 = used2 + n.
Proof.
  intros n.
  apply helper.
Qed.

Lemma unused_lemma2 : forall n : nat, n * 0 = 0.
Proof.
  intros n.
  rewrite Nat.mul_0_r.
  reflexivity.
Qed.

Theorem target : forall n : nat, n + used2 = used2 + n.
Proof.
  apply used_lemma.
Qed.
