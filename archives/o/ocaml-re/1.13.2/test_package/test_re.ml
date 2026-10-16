(* Consumer test for the packaged ocaml-re 1.13.2 (findlib library `re`).

   Exercises the real public API of the packaged library: Perl/Posix/Glob
   syntax compilation, group extraction, glob matching (positive and
   negative), split, replace_string and the Str compatibility layer. *)

let failures = ref 0

let check name cond =
  if cond then Printf.printf "ok - %s\n" name
  else (incr failures; Printf.printf "FAIL - %s\n" name)

let () =
  (* Perl syntax: extract YYYY-MM-DD date parts *)
  let date = Re.Perl.compile_pat "(\\d{4})-(\\d{2})-(\\d{2})" in
  (match Re.exec_opt date "release 2026-10-12 done" with
   | Some g ->
     check "perl groups"
       (Re.Group.get g 1 = "2026" && Re.Group.get g 2 = "10"
        && Re.Group.get g 3 = "12")
   | None -> check "perl groups" false);

  (* Glob syntax: brace expansion + wildcard, positive and negative *)
  let glob = Re.compile (Re.Glob.glob "*.ml") in
  check "glob accept" (Re.execp glob "foo.ml");
  check "glob reject" (not (Re.execp glob "foo.c"));

  (* Posix anchored class, positive and negative *)
  let px = Re.Posix.compile_pat "^[a-z]+$" in
  check "posix accept" (Re.execp px "hello");
  check "posix reject" (not (Re.execp px "Hello1"));

  (* split and replace_string over core combinators *)
  let comma = Re.compile (Re.char ',') in
  check "split" (Re.split comma "a,b,c" = ["a"; "b"; "c"]);
  check "replace_string" (Re.replace_string comma ~by:";" "a,b,c" = "a;b;c");

  (* Str compatibility layer *)
  check "str string_match" (Re.Str.string_match (Re.Str.regexp "a+b") "aaab" 0);
  check "str regexp reject" (not (Re.Str.string_match (Re.Str.regexp "^b+$") "aaab" 0));

  print_string
    (if !failures = 0 then "ALL TESTS PASSED\n" else "SOME TESTS FAILED\n");
  if !failures > 0 then exit 1
