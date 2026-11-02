From Stdlib Require Import List.
Import ListNotations.

Definition unused_list : list nat := [1; 2; 3].
Definition sample : list nat := [0; 1].

Lemma unused_app_nil : forall (A : Type) (xs : list A), xs ++ [] = xs.
Proof.
  intros A xs.
  apply app_nil_r.
Qed.

Lemma app_nil_sample : forall xs : list nat, xs ++ [] = xs.
Proof.
  intros xs.
  apply app_nil_r.
Qed.

Theorem target : forall xs : list nat, xs ++ [] = xs.
Proof.
  apply app_nil_sample.
Qed.
