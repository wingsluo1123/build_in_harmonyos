(* test_package consumer test - ocaml-compiler-libs 0.12.4.
   Consumes the repackaged compiler libraries: builds a Parsetree node with
   Ocaml_common.Ast_helper, pretty-prints it with Ocaml_common.Pprintast,
   parses source with Ocaml_common.Parse and exercises Longident/Location. *)

open Ocaml_common

let failures = ref 0

let check name cond =
  if cond then Printf.printf "ok - %s\n" name
  else (
    incr failures;
    Printf.printf "FAIL - %s\n" name)

let () =
  let expr = Ast_helper.Exp.constant (Ast_helper.Const.int 42) in
  let buf = Buffer.create 16 in
  let fmt = Format.formatter_of_buffer buf in
  Pprintast.expression fmt expr;
  Format.pp_print_flush fmt ();
  check "Pprintast.expression" (Buffer.contents buf = "42");

  let structure = Parse.implementation (Lexing.from_string "let x = 1") in
  check "Parse.implementation" (List.length structure = 1);

  let lid =
    Location.mkloc
      (Longident.Ldot (Longident.Lident "Stdlib", "print_endline"))
      Location.none
  in
  check "Longident.last" (Longident.last lid.txt = "print_endline");
  check "Location.none" (Location.none = Location.none);

  if !failures = 0 then print_endline "ALL TESTS PASSED"
  else (
    Printf.printf "%d FAILURES\n" !failures;
    exit 1)
