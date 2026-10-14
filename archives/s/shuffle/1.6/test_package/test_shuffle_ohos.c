/* HarmonyOS-specific consumer test for patches/0001-open-o-creat-mode.patch.
 *
 * Upstream creates the output file with open(path, O_WRONLY|O_CREAT) and no
 * mode argument.  open() is variadic and the OHOS musl libc reads the mode
 * with va_arg() when O_CREAT is set, so an unpatched build creates the file
 * with whatever bits were left in the argument register (0155 - no access
 * for the owner - when run under qemu-aarch64).  The patched tool must create
 * the file with 0666 filtered by the umask.  Checked here for two umasks: the
 * mode of the freshly created output file must equal the mode of a reference
 * file that the test itself creates with open(O_CREAT, 0666) in the same
 * directory under the same umask (so a file system that normalises mode bits
 * treats both alike), and the owner must be able to read and write it. */
#include "shuffle_test.h"

#define N 200

static void create_with_umask(mode_t mask, mode_t want)
{
  /* want is what a mode-honouring file system gives: 0666 & ~mask */
  size_t len, outlen;
  char *in = gen_lines(N, &len), *inp = path_in("ohos-in.txt"), *outp = path_in("ohos-out.txt");
  char *refp = path_in("ohos-ref.txt");
  char *argv[] = {(char *) g_bin, inp, outp, NULL};
  result_t r;
  struct stat sb, rb;
  mode_t old = umask(mask);
  char *out;
  int fd;

  write_file(inp, in, len);
  unlink(outp);
  unlink(refp);
  fd = open(refp, O_WRONLY|O_CREAT|O_EXCL, 0666);
  CHECK(fd >= 0 && fstat(fd, &rb) == 0, "cannot create reference file: %s", strerror(errno));
  if (fd >= 0) close(fd);
  CHECK(run(argv, NULL, NULL, 0, &r) == 0, "cannot run shuffle");
  umask(old);
  CHECK(r.status == 0, "exit status %d, stderr: %s", r.status, r.err ? r.err : "");
  CHECK(stat(outp, &sb) == 0, "output file was not created: %s", strerror(errno));
  if (stat(outp, &sb) == 0) {
    CHECK((sb.st_mode & 07777) == (rb.st_mode & 07777),
          "umask %04o: output file mode is %04o, a file created with mode 0666 gets %04o (expected %04o)",
          (unsigned) mask, (unsigned) (sb.st_mode & 07777), (unsigned) (rb.st_mode & 07777),
          (unsigned) want);
    CHECK((sb.st_mode & 0600) == 0600, "owner cannot read and write the output file (mode %04o)",
          (unsigned) (sb.st_mode & 07777));
  }
  out = read_all(outp, &outlen);
  CHECK(out != NULL, "output file is not readable by its owner");
  CHECK(out && check_permutation(out, outlen, N, NULL), "output file is not a permutation of the input");
  free(out);
  free_result(&r);
  free(in);
  free(inp);
  free(outp);
  free(refp);
}

static void case_create_umask_022(void)
{
  create_with_umask(022, 0644);
}

static void case_create_umask_077(void)
{
  create_with_umask(077, 0600);
}

int main(int argc, char *argv[])
{
  int rc = setup(argc, argv);
  if (rc) return rc;
  run_case("new output file, umask 022", case_create_umask_022);
  run_case("new output file, umask 077", case_create_umask_077);
  return finish("shuffle OHOS-specific tests");
}
