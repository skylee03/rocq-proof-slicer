From Stdlib Require Import Arith.PeanoNat.

Fixpoint plus_two (n : nat) : nat :=
  match n with
  | 0 => 2
  | S k => S (plus_two k)
  end.

Definition unused_fix : nat := plus_two 100.

Lemma plus_two_zero : plus_two 0 = 2.
Proof.
  reflexivity.
Qed.

Theorem target : plus_two 0 = 2.
Proof.
  apply plus_two_zero.
Qed.
