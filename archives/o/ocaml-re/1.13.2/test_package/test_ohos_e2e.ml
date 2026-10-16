(* HarmonyOS end-to-end consumer case for the packaged ocaml-re.

   Writes a real key=value report file, regex-parses every line with the
   packaged re library, aggregates the results, writes a result file and
   reads it back — exercising the library on the real OHOS filesystem. *)

let () =
  let path = "re_e2e_sample.txt" in
  let oc = open_out path in
  output_string oc "alpha=1\nbeta=22\ngamma=333\n";
  close_out oc;

  let re = Re.Perl.compile_pat "^([a-z]+)=([0-9]+)$" in
  let ic = open_in path in
  let lines = ref 0 and digits = ref 0 in
  (try
     while true do
       let line = input_line ic in
       incr lines;
       match Re.exec_opt re line with
       | Some g -> digits := !digits + String.length (Re.Group.get g 2)
       | None -> ()
     done
   with End_of_file -> ());
  close_in ic;

  let ok = !lines = 3 && !digits = 6 in
  let out = open_out "re_e2e_result.txt" in
  output_string out
    (if ok then "ALL OHOS E2E PASSED (3 lines, 6 digits)\n"
     else Printf.sprintf "E2E FAILED (lines=%d digits=%d)\n" !lines !digits);
  close_out out;

  let ic2 = open_in "re_e2e_result.txt" in
  let result = input_line ic2 in
  close_in ic2;
  print_endline result;
  if not ok then exit 1
