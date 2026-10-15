(* HarmonyOS-specific end-to-end consumer case (鸿蒙特有测试):
   real file I/O on the OHOS worker filesystem - serialize a structured
   S-expression config to a file, read it back byte-for-byte, verify the
   serialized fields and deterministic re-serialization. sexplib0 has no
   parser, so verification works on the serialized text plus the in-memory
   structure. *)

open Sexplib0

let fail msg =
  Printf.printf "FAIL: %s\n" msg;
  exit 1

let () =
  let path = "sexplib0_ohos_e2e.sexp" in
  let config =
    Sexp.List
      [ Sexp.List [ Sexp.Atom "name"; Sexp.Atom "ohos" ];
        Sexp.List [ Sexp.Atom "arch"; Sexp.Atom "aarch64" ];
        Sexp.List
          [ Sexp.Atom "values";
            Sexp_conv.sexp_of_list Sexp_conv.sexp_of_int [ 1; 2; 3 ] ];
        Sexp.List [ Sexp.Atom "enabled"; Sexp_conv.sexp_of_bool true ] ]
  in
  let text = Sexp.to_string config in
  let oc = open_out path in
  output_string oc text;
  close_out oc;

  let ic = open_in path in
  let n = in_channel_length ic in
  let buf = really_input_string ic n in
  close_in ic;
  if buf <> text then fail "file content mismatch";

  let contains s =
    let ls = String.length s and lb = String.length buf in
    let rec go i = i + ls <= lb && (String.sub buf i ls = s || go (i + 1)) in
    go 0
  in
  if not (contains "(arch aarch64)") then fail "arch field missing";
  if not (contains "(values(1 2 3))") then fail "values field missing";
  if not (contains "(enabled true)") then fail "enabled field missing";

  if Sexp.to_string config <> text then fail "serialization not deterministic";

  Sys.remove path;
  print_endline "ALL OHOS E2E PASSED"
