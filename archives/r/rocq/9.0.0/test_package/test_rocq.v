(* test_rocq.v -- Rocq 9.0.0 test file *)
(* Verifies basic Rocq functionality: definitions, proofs, computations *)

(* Simple natural number definition *)
Definition nat_zero := 0.
Definition nat_one := 1.

(* Addition is correct *)
Theorem one_plus_one : 1 + 1 = 2.
Proof. reflexivity. Qed.

(* List definition *)
Inductive my_list (A : Type) : Type :=
  | my_nil : my_list A
  | my_cons : A -> my_list A -> my_list A.

(* Append function *)
Fixpoint my_append {A : Type} (l1 l2 : my_list A) : my_list A :=
  match l1 with
  | my_nil => l2
  | my_cons x xs => my_cons A x (my_append xs l2)
  end.

(* Append of empty list is identity *)
Theorem append_nil :
  forall (A : Type) (l : my_list A), my_append (my_nil A) l = l.
Proof. intros A l. simpl. reflexivity. Qed.

(* Boolean definition *)
Inductive my_bool : Type :=
  | my_true : my_bool
  | my_false : my_bool.

(* Negation *)
Definition my_not (b : my_bool) : my_bool :=
  match b with
  | my_true => my_false
  | my_false => my_true
  end.

(* Double negation *)
Theorem double_neg :
  forall b : my_bool, my_not (my_not b) = b.
Proof.
  intros b. destruct b; reflexivity.
Qed.
