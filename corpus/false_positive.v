From Stdlib Require Import Arith.PeanoNat.

Definition helper : nat := 42.

Lemma target_lemma : forall helper : nat, helper = helper.
Proof.
  reflexivity.
Qed.

Theorem target : forall n : nat, n = n.
Proof.
  intros n.
  apply target_lemma.
Qed.
