From Stdlib Require Import Arith.PeanoNat.

Definition noise1 : nat := 1.
Definition noise2 : nat := noise1 + 1.

Lemma noise_lemma : forall n : nat, n + 0 = n.
Proof.
  intros n.
  rewrite Nat.add_0_r.
  reflexivity.
Qed.

Theorem broken : forall n : nat, n + 1 = n.
Proof.
  intros n.
  reflexivity.
Qed.
