/* Consumer test: drive the packaged bin/shuffle the way a user does and check
 * the shuffled output - same multiset of lines, different order - for every
 * input path of the tool (file via mmap, redirected stdin, pipe via read()),
 * plus its error contract. */
#include "shuffle_test.h"

#define N_FILE 1000
#define N_PIPE 20000 /* ~240 KB: several rounds of the read()/realloc() loop */

static void case_file_to_file(void)
{
  size_t len;
  char *in = gen_lines(N_FILE, &len), *inp = path_in("in.txt"), *outp = path_in("out.txt");
  char *argv[] = {(char *) g_bin, inp, outp, NULL};
  result_t r;
  int identity = 1;
  size_t outlen;
  char *out;

  write_file(inp, in, len);
  unlink(outp);
  CHECK(run(argv, NULL, NULL, 0, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 0, "exit status %d, stderr: %s", r.status, r.err ? r.err : "");
  out = read_all(outp, &outlen);
  CHECK(out != NULL, "output file was not created");
  if (out) {
    CHECK(check_permutation(out, outlen, N_FILE, &identity), "output is not a permutation of the input");
    CHECK(!identity, "%d lines came back in the original order", N_FILE);
  }
  free(out);
  free_result(&r);
  free(in);
  free(inp);
  free(outp);
}

static void case_stdin_file_to_stdout(void)
{
  size_t len;
  char *in = gen_lines(N_FILE, &len), *inp = path_in("stdin.txt");
  char *argv[] = {(char *) g_bin, NULL};
  result_t r;
  int identity = 1;

  write_file(inp, in, len);
  CHECK(run(argv, inp, NULL, 0, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 0, "exit status %d, stderr: %s", r.status, r.err ? r.err : "");
  CHECK(r.out && check_permutation(r.out, r.outlen, N_FILE, &identity), "stdout is not a permutation");
  CHECK(!identity, "lines came back in the original order");
  free_result(&r);
  free(in);
  free(inp);
}

static void case_pipe_input(void)
{
  size_t len;
  char *in = gen_lines(N_PIPE, &len);
  char *argv[] = {(char *) g_bin, (char *) "-", (char *) "-", NULL};
  result_t r;
  int identity = 1;

  CHECK(run(argv, NULL, in, len, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 0, "exit status %d, stderr: %s", r.status, r.err ? r.err : "");
  CHECK(r.out && check_permutation(r.out, r.outlen, N_PIPE, &identity),
        "pipe input: stdout is not a permutation (got %zu bytes, want %zu)", r.outlen, len);
  CHECK(!identity, "pipe input came back in the original order");
  free_result(&r);
  free(in);
}

static void case_single_line(void)
{
  char *argv[] = {(char *) g_bin, NULL};
  result_t r;

  CHECK(run(argv, NULL, "only\n", 5, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 0, "exit status %d", r.status);
  CHECK(r.out && strcmp(r.out, "only\n") == 0, "single line changed: '%s'", r.out ? r.out : "(null)");
  free_result(&r);
}

static void case_error_contract(void)
{
  char *missing = path_in("does-not-exist.txt");
  char *noeol = path_in("noeol.txt");
  char *a1[] = {(char *) g_bin, missing, NULL};
  char *a2[] = {(char *) g_bin, noeol, NULL};
  char *a3[] = {(char *) g_bin, (char *) "a", (char *) "b", (char *) "c", NULL};
  result_t r;

  unlink(missing);
  CHECK(run(a1, NULL, NULL, 0, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 1, "missing input: exit status %d, want 1", r.status);
  CHECK(r.err && strstr(r.err, "No such file or directory"), "missing input: stderr '%s'", r.err ? r.err : "");
  CHECK(r.outlen == 0, "missing input produced output");
  free_result(&r);

  write_file(noeol, "alpha\nbeta", 10);
  CHECK(run(a2, NULL, NULL, 0, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 1, "no trailing newline: exit status %d, want 1", r.status);
  CHECK(r.err && strstr(r.err, "Missing newline at eof"), "no trailing newline: stderr '%s'", r.err ? r.err : "");
  free_result(&r);

  CHECK(run(a3, NULL, NULL, 0, &r) == 0, "cannot run shuffle");
  CHECK(r.status == 1, "too many arguments: exit status %d, want 1", r.status);
  CHECK(r.err && strstr(r.err, "Usage"), "too many arguments: stderr '%s'", r.err ? r.err : "");
  free_result(&r);
  free(missing);
  free(noeol);
}

int main(int argc, char *argv[])
{
  int rc = setup(argc, argv);
  if (rc) return rc;
  run_case("file-to-file (mmap path)", case_file_to_file);
  run_case("redirected stdin to stdout", case_stdin_file_to_stdout);
  run_case("pipe input (read path, 240 KB)", case_pipe_input);
  run_case("single line", case_single_line);
  run_case("error contract", case_error_contract);
  return finish("shuffle consumer tests");
}
