(* HarmonyOS-specific end-to-end consumer case (鸿蒙特有测试):
   real file I/O on the OHOS worker filesystem - serialize the registry
   contents to a file, read it back, and re-verify registration and lookup
   against the packaged library. *)

open Ppx_derivers

type Ppx_derivers.deriver += Ohos_deriver of string

let fail msg =
  Printf.printf "FAIL: %s\n" msg;
  exit 1

let () =
  register "ohos_deriver" (Ohos_deriver "aarch64");

  let path = "ppx_derivers_ohos_e2e.txt" in
  let names = List.map fst (derivers ()) in
  let oc = open_out path in
  List.iter (fun n -> output_string oc (n ^ "\n")) names;
  close_out oc;

  let ic = open_in path in
  let n = in_channel_length ic in
  let buf = really_input_string ic n in
  close_in ic;
  if buf = "" then fail "registry file empty";

  let lines = String.split_on_char '\n' buf in
  if not (List.mem "ohos_deriver" lines) then fail "registered name not persisted";

  (match lookup "ohos_deriver" with
  | Some (Ohos_deriver "aarch64") -> ()
  | _ -> fail "lookup mismatch after file round-trip");

  Sys.remove path;
  print_endline "ALL OHOS E2E PASSED"
