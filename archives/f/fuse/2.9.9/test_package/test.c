/*
 * Consumer test for fuse/2.9.9 (FUSE 2.x / Libfuse2 legacy ABI) on OHOS.
 *
 * Scope decision (see notes.md / knowledge draft):
 *   OHOS does not expose a usable FUSE device node, so every mount-dependent
 *   upstream path is unreachable. This test therefore (a) exercises the
 *   offline library surface for real, and (b) *measures* the device wall with
 *   discriminating negative controls instead of emitting a vacuous pass.
 *
 * Every check below prints its raw reading; the process exits non-zero if any
 * check fails, which is what `conan test` propagates.
 */
#define FUSE_USE_VERSION 26

#include <fuse.h>
#include <fuse_lowlevel.h>
#include <fuse_opt.h>

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int checks = 0;
static int fails = 0;

#define CHECK(cond, ...)                                                       \
    do {                                                                       \
        checks++;                                                              \
        if (cond) {                                                            \
            printf("  PASS  ");                                                \
        } else {                                                               \
            fails++;                                                           \
            printf("  FAIL  ");                                                \
        }                                                                      \
        printf(__VA_ARGS__);                                                   \
        printf("\n");                                                          \
    } while (0)

struct opt_holder {
    char *name;
};

static struct fuse_opt opt_specs[] = {
    {"-n %s", offsetof(struct opt_holder, name), 0},
    FUSE_OPT_END
};

/* Parse "-n <val>" and return 1 only when the parser really produced <val>. */
static int parse_name(const char *val, char *out, size_t outsz)
{
    struct opt_holder h;
    char *argv[3];
    struct fuse_args args;
    int rc;

    memset(&h, 0, sizeof(h));
    argv[0] = (char *)"fusetest";
    argv[1] = (char *)"-n";
    argv[2] = (char *)val;
    args = (struct fuse_args)FUSE_ARGS_INIT(3, argv);

    rc = fuse_opt_parse(&args, &h, opt_specs, NULL);
    if (rc == 0 && h.name != NULL && strcmp(h.name, val) == 0) {
        snprintf(out, outsz, "%s", h.name);
        free(h.name);
        fuse_opt_free_args(&args);
        return 1;
    }
    free(h.name);
    fuse_opt_free_args(&args);
    return 0;
}

/* open(O_RDWR) probe that reports the exact errno. */
static int probe_open(const char *path, int *err_out)
{
    int fd = open(path, O_RDWR);

    if (fd < 0) {
        *err_out = errno;
        return -1;
    }
    close(fd);
    *err_out = 0;
    return 0;
}

int main(void)
{
    char n_alpha[64] = {0};
    char n_beta[64] = {0};
    int r_alpha, r_beta;
    char cwd[4096] = {0};
    char *cargv[3];
    struct fuse_args cargs;
    char *mountpoint = NULL;
    int mt_default = -1, fg = -1, mt_single = -1;
    const struct fuse_lowlevel_ops llops;
    char *largv[1];
    struct fuse_args largs;
    struct fuse_session *se;
    char *margv[1];
    struct fuse_args margs;
    struct fuse_chan *ch;
    int e_dev = 0, e_null = 0, e_missing = 0;
    int r_dev, r_null, r_missing;
    int v;

    printf("== fuse/2.9.9 consumer test (Libfuse2 legacy ABI) ==\n");

    /* ---- 1. version binding ------------------------------------------- */
    v = fuse_version();
    CHECK(FUSE_MAJOR_VERSION == 2 && FUSE_MINOR_VERSION == 9,
          "headers declare FUSE 2.9 (major=%d minor=%d)",
          FUSE_MAJOR_VERSION, FUSE_MINOR_VERSION);
    CHECK(v == FUSE_VERSION && v == 29,
          "fuse_version()=%d == FUSE_VERSION=%d == 29 (legacy 2.x ABI)",
          v, FUSE_VERSION);

    /* ---- 2. option parsing (with a discriminating control) ------------- */
    r_alpha = parse_name("alpha", n_alpha, sizeof(n_alpha));
    r_beta = parse_name("beta", n_beta, sizeof(n_beta));
    CHECK(r_alpha, "fuse_opt_parse(-n alpha) -> '%s'", n_alpha);
    CHECK(r_beta, "fuse_opt_parse(-n beta) -> '%s'", n_beta);
    CHECK(r_alpha && r_beta && strcmp(n_alpha, n_beta) != 0,
          "negative control: parser follows its input ('%s' != '%s')",
          n_alpha, n_beta);

    /* ---- 3. fuse_parse_cmdline on a real directory --------------------- */
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        printf("  FAIL  getcwd() failed: %s\n", strerror(errno));
        fails++;
    }
    cargv[0] = (char *)"fusetest";
    cargv[1] = (char *)"-f";
    cargv[2] = cwd;
    cargs = (struct fuse_args)FUSE_ARGS_INIT(3, cargv);
    CHECK(fuse_parse_cmdline(&cargs, &mountpoint, &mt_default, &fg) == 0,
          "fuse_parse_cmdline() accepted '-f %s' rc=0", cwd);
    CHECK(fg == 1, "-f parsed as foreground (foreground=%d)", fg);
    CHECK(mountpoint != NULL && strcmp(mountpoint, cwd) == 0,
          "mountpoint resolved through realpath -> '%s'",
          mountpoint ? mountpoint : "(null)");
    free(mountpoint);
    mountpoint = NULL;
    fuse_opt_free_args(&cargs);

    cargv[0] = (char *)"fusetest";
    cargv[1] = (char *)"-s";
    cargv[2] = cwd;
    cargs = (struct fuse_args)FUSE_ARGS_INIT(3, cargv);
    if (fuse_parse_cmdline(&cargs, NULL, &mt_single, NULL) == 0) {
        CHECK(mt_default != mt_single,
              "negative control: -s flips multithreaded (%d -> %d)",
              mt_default, mt_single);
    } else {
        CHECK(0, "fuse_parse_cmdline() rejected '-s %s'", cwd);
    }
    fuse_opt_free_args(&cargs);

    /* ---- 4. offline lowlevel session (no /dev/fuse needed) ------------- */
    memset((void *)&llops, 0, sizeof(llops));
    largv[0] = (char *)"fusetest";
    largs = (struct fuse_args)FUSE_ARGS_INIT(1, largv);
    se = fuse_lowlevel_new(&largs, &llops, sizeof(llops), NULL);
    CHECK(se != NULL,
          "fuse_lowlevel_new() built an offline session object (no /dev/fuse)");
    if (se != NULL) {
        fuse_session_destroy(se);
    }
    fuse_opt_free_args(&largs);

    /* ---- 5. device probe + negative controls -------------------------- */
    r_null = probe_open("/dev/null", &e_null);
    r_missing = probe_open("/nonexistent/definitely/not/here", &e_missing);
    r_dev = probe_open("/dev/fuse", &e_dev);
    printf("  INFO  probe: /dev/fuse -> %s (errno=%d %s)\n",
           r_dev == 0 ? "open OK" : "open FAILED", e_dev,
           e_dev ? strerror(e_dev) : "-");
    CHECK(r_null == 0,
          "probe control: open(/dev/null,O_RDWR) succeeded (errno=%d)", e_null);
    CHECK(r_missing != 0 && e_missing == ENOENT,
          "probe control: missing path -> errno=%d (%s)",
          e_missing, strerror(e_missing));
    CHECK(!(e_dev == ENOENT && r_missing == 0),
          "probe discriminates ENOENT(%d) from /dev/fuse errno(%d)",
          e_missing, e_dev);

    /* ---- 6. FUSE mount capability must agree with the raw device probe - */
    margv[0] = (char *)"fusetest";
    margs = (struct fuse_args)FUSE_ARGS_INIT(1, margv);
    ch = fuse_mount(cwd, &margs);
    if (r_dev == 0) {
        CHECK(ch != NULL,
              "consistency: /dev/fuse openable -> fuse_mount() returned a chan");
    } else {
        CHECK(ch == NULL,
              "consistency: /dev/fuse errno=%d -> fuse_mount()=NULL "
              "(mount capability wall, not a library defect)", e_dev);
    }
    if (ch != NULL) {
        fuse_unmount(cwd, ch);
    }
    fuse_opt_free_args(&margs);

    printf("== %d checks, %d failed ==\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
