(* test_package consumer test - ppx_derivers 1.2.1.
   Consumes the shared deriver registry: extends the exported extensible
   type, registers a deriver, looks it up and checks the negative controls
   (unknown lookup, duplicate registration). *)

open Ppx_derivers

type Ppx_derivers.deriver += My_test_deriver of int

let failures = ref 0

let check name cond =
  if cond then Printf.printf "ok - %s\n" name
  else (
    incr failures;
    Printf.printf "FAIL - %s\n" name)

let () =
  register "my_test_deriver" (My_test_deriver 42);
  check "lookup registered"
    (match lookup "my_test_deriver" with
    | Some (My_test_deriver 42) -> true
    | _ -> false);
  check "derivers() contains entry" (List.mem_assoc "my_test_deriver" (derivers ()));
  check "unknown lookup returns None" (lookup "no_such_deriver" = None);
  let dup_raised =
    try
      register "my_test_deriver" (My_test_deriver 0);
      false
    with _ -> true
  in
  check "duplicate registration raises" dup_raised;

  if !failures = 0 then print_endline "ALL TESTS PASSED"
  else (
    Printf.printf "%d FAILURES\n" !failures;
    exit 1)
