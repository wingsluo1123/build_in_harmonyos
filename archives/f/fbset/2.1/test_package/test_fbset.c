/* test_fbset.c — consumer test for fbset/2.1 (CLI tool, R34).
 *
 * fbset is not linkable (no library), so this driver executes the packaged
 * binary that test_package/conanfile.py passes as argv[1] and checks the
 * observable behaviour of the FB ioctl tool:
 *
 *   1. `--help` → informational request: exit status 0, program banner on
 *      stdout and the option list on stderr.
 *   2. `-V`     → the upstream version banner "Version 2.1 (23/06/1999)";
 *      upstream prints it and then performs the query, so a machine without a
 *      frame buffer ends with status 1 and a device diagnostic — both
 *      outcomes are accepted, an unexplained failure is not.
 *   3. `-s`     → a real query: opens the device and issues
 *      FBIOGET_VSCREENINFO.  With /dev/fb* present the video mode must be
 *      printed (status 0); without a frame buffer the program must report
 *      which device/ioctl failed.  Both are valid, silent/crashing is not.
 *
 * The binary path is argv[1], so deleting the package artifacts makes
 * execve() fail and the test fails (CI L1e destructive negative test).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define OUT_MAX 4096
#define ERR_MAX 8192

#define BANNER "Linux Frame Buffer Device Configuration"
#define VERSION "Version 2.1 (23/06/1999)"

static int failures = 0;
static int assertions = 0;

static void check(int cond, const char *what)
{
    assertions++;
    printf("%s  %s\n", cond ? "[ok]  " : "[FAIL]", what);
    if (!cond)
        failures++;
}

static void read_all(int fd, char *buf, size_t cap)
{
    size_t used = 0;
    ssize_t n;

    while (used + 1 < cap &&
           (n = read(fd, buf + used, cap - used - 1)) > 0)
        used += (size_t)n;
    buf[used] = '\0';
    close(fd);
}

/* Run bin (argv[0]-style, NULL terminated), capture stdout/stderr and return
 * the child's exit status; -1 when the child could not be started or was
 * killed by a signal. */
static int run_capture(char *const args[], char *out, size_t out_cap,
                       char *err, size_t err_cap)
{
    int outp[2], errp[2];
    pid_t pid;
    int status;

    out[0] = '\0';
    err[0] = '\0';
    if (pipe(outp) != 0 || pipe(errp) != 0)
        return -1;
    pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        dup2(outp[1], STDOUT_FILENO);
        dup2(errp[1], STDERR_FILENO);
        close(outp[0]);
        close(outp[1]);
        close(errp[0]);
        close(errp[1]);
        execv(args[0], args);
        _exit(127);
    }
    close(outp[1]);
    close(errp[1]);
    read_all(outp[0], out, out_cap);
    read_all(errp[0], err, err_cap);
    if (waitpid(pid, &status, 0) < 0)
        return -1;
    if (!WIFEXITED(status))
        return -1;
    return WEXITSTATUS(status);
}

static int mentions_device(const char *err)
{
    return strstr(err, "/dev/fb") != NULL || strstr(err, "ioctl") != NULL;
}

int main(int argc, char **argv)
{
    char out[OUT_MAX], err[ERR_MAX];
    char *help_args[3];
    char *ver_args[3];
    char *show_args[3];
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-fbset>\n", argv[0]);
        return 2;
    }

    /* 1. --help must be a successful informational request */
    help_args[0] = argv[1];
    help_args[1] = "--help";
    help_args[2] = NULL;
    rc = run_capture(help_args, out, sizeof out, err, sizeof err);
    check(rc == 0, "--help exits with status 0");
    check(strstr(out, BANNER) != NULL,
          "--help prints the program banner on stdout");
    check(strstr(err, "Usage:") != NULL,
          "--help prints the option list on stderr");

    /* 2. -V prints the upstream version banner */
    ver_args[0] = argv[1];
    ver_args[1] = "-V";
    ver_args[2] = NULL;
    rc = run_capture(ver_args, out, sizeof out, err, sizeof err);
    check(strstr(out, VERSION) != NULL,
          "-V prints the \"Version 2.1 (23/06/1999)\" banner");
    check(rc == 0 || (rc == 1 && mentions_device(err)),
          "-V ends with the video mode or a well-formed device diagnostic");

    /* 3. -s performs the real FBIOGET_VSCREENINFO query */
    show_args[0] = argv[1];
    show_args[1] = "-s";
    show_args[2] = NULL;
    rc = run_capture(show_args, out, sizeof out, err, sizeof err);
    check(rc == 0 ? out[0] != '\0' : mentions_device(err),
          "-s prints the video mode, or names the missing frame buffer device");

    printf("%d assertion(s), %d failure(s)\n", assertions, failures);
    return failures ? 1 : 0;
}
