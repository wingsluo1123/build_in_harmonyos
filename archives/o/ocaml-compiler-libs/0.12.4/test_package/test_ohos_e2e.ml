(* HarmonyOS-specific end-to-end consumer case (鸿蒙特有测试):
   real file I/O on the OHOS worker filesystem - write an OCaml source file,
   parse it back with the packaged compiler libraries, pretty-print the
   parsed structure and verify the round-trip. *)

open Ocaml_common

let fail msg =
  Printf.printf "FAIL: %s\n" msg;
  exit 1

let contains haystack needle =
  let lh = String.length haystack and ln = String.length needle in
  let rec go i = i + ln <= lh && (String.sub haystack i ln = needle || go (i + 1)) in
  go 0

let () =
  let path = "ocl_ohos_e2e.ml" in
  let oc = open_out path in
  output_string oc "let answer = 42\n";
  close_out oc;
  if not (Sys.file_exists path) then fail "file not created";

  let ic = open_in path in
  let n = in_channel_length ic in
  let buf = really_input_string ic n in
  close_in ic;
  if buf = "" then fail "empty input";

  let structure = Parse.implementation (Lexing.from_string buf) in
  if List.length structure <> 1 then fail "expected 1 structure item";

  let out = Buffer.create 32 in
  let fmt = Format.formatter_of_buffer out in
  Pprintast.structure fmt structure;
  Format.pp_print_flush fmt ();
  let printed = Buffer.contents out in
  if not (contains printed "let answer = 42") then fail "printed text mismatch";

  Sys.remove path;
  print_endline "ALL OHOS E2E PASSED"
