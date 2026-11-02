From Stdlib Require Import Bool.

Definition unused_bool : bool := true.
Definition flag : bool := false.

Lemma unused_negb : forall b : bool, negb (negb b) = b.
Proof.
  apply negb_involutive.
Qed.

Lemma flag_false : flag = false.
Proof.
  reflexivity.
Qed.

Theorem target : flag = false.
Proof.
  apply flag_false.
Qed.
