(* test_package consumer test - sexplib0 0.17.0.
   Exercises the packaged library end-to-end: Sexp construction/printing,
   the Sexp_conv converters for base types and Sexpable. sexplib0 itself has
   no textual parser (parsing lives in the separate parsexp package), so all
   values are built directly and converted with the packaged converters. *)

open Sexplib0

let failures = ref 0

let check name cond =
  if cond then Printf.printf "ok - %s\n" name
  else (
    incr failures;
    Printf.printf "FAIL - %s\n" name)

module Int_sexpable : Sexpable.S with type t = int = struct
  type t = int

  let t_of_sexp = Sexp_conv.int_of_sexp
  let sexp_of_t = Sexp_conv.sexp_of_int
end

let () =
  let sample =
    Sexp.List [ Sexp.Atom "hello"; Sexp.List [ Sexp.Atom "world"; Sexp.Atom "42" ] ]
  in
  check "Sexp.to_string" (Sexp.to_string sample = "(hello(world 42))");
  check "Sexp.to_string_mach" (Sexp.to_string_mach sample = Sexp.to_string sample);

  let hum = Sexp.to_string_hum sample in
  let contains s =
    let ls = String.length s and lh = String.length hum in
    let rec go i = i + ls <= lh && (String.sub hum i ls = s || go (i + 1)) in
    go 0
  in
  check "Sexp.to_string_hum" (contains "hello");

  check "Sexp.equal" (Sexp.equal (Sexp.Atom "x") (Sexp.Atom "x"));
  check "Sexp.compare" (Sexp.compare (Sexp.Atom "a") (Sexp.Atom "b") < 0);
  check "Sexp_conv.sexp_of_int" (Sexp.to_string (Sexp_conv.sexp_of_int 42) = "42");
  check "Sexp_conv.int_of_sexp" (Sexp_conv.int_of_sexp (Sexp.Atom "7") = 7);
  check "Sexp_conv.sexp_of_string"
    (Sexp.to_string (Sexp_conv.sexp_of_string "hi") = "hi");
  check "Sexp_conv.string_of_sexp"
    (Sexp_conv.string_of_sexp (Sexp.Atom "hi") = "hi");
  check "Sexp_conv.sexp_of_bool"
    (Sexp.to_string (Sexp_conv.sexp_of_bool true) = "true");
  check "Sexp_conv.bool_of_sexp" (Sexp_conv.bool_of_sexp (Sexp.Atom "false") = false);
  check "Sexp_conv.sexp_of_list"
    (Sexp.to_string (Sexp_conv.sexp_of_list Sexp_conv.sexp_of_int [ 1; 2; 3 ])
    = "(1 2 3)");
  check "Sexp_conv.list_of_sexp"
    (Sexp_conv.list_of_sexp Sexp_conv.int_of_sexp
       (Sexp.List [ Sexp.Atom "1"; Sexp.Atom "2" ])
    = [ 1; 2 ]);
  check "Sexpable round-trip"
    (Int_sexpable.t_of_sexp (Int_sexpable.sexp_of_t 99) = 99);
  check "Sexp.message"
    (Sexp.to_string
       (Sexp.message "error"
          [ ("x", Sexp_conv.sexp_of_int 42); ("", Sexp.Atom "raw") ])
    = "(error(x 42)raw)");

  if !failures = 0 then print_endline "ALL TESTS PASSED"
  else (
    Printf.printf "%d FAILURES\n" !failures;
    exit 1)
