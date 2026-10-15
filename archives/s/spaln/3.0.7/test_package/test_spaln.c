/* spaln OHOS consumer test.
 *
 * This program is compiled by CMake with the OHOS aarch64 toolchain and
 * executed on the target, so a successful run already proves the packaged
 * binaries are loadable by the OHOS loader.  On top of that it makes ten
 * independent assertions against the packaged executables and parameter
 * tables:
 *
 *   1. `spaln` with no arguments prints the version banner (SPALN_{arch} 3.0.7)
 *   2. the banner advertises the aarch64 NEON SIMD path (_ARM_NEON)
 *   3. `spaln` with no arguments prints the usage screen
 *   4. `sortgrcd` with no arguments prints its version banner
 *   5. `makdbs` with no arguments prints its version banner
 *   6. every packaged executable is present in <pkg>/bin
 *   7. the packaged parameter table directory exists and is populated
 *   8. the AlnParam table is readable (the binaries' baked-in table path works)
 *   9. `makmdm` regenerates mdm_cmp matching the packaged PAM composition
 *  10. `makmdm` regenerates an mdm_mtx of the same geometry as the packaged one
 *
 * Usage: test_spaln <path-to-packaged-spaln>
 */
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define OUT_SIZE 65536
#define TABLE_MIN_ENTRIES 250

#define SPALN_VERSION_LINE "version 3.0.7"

static const char *const PROGRAMS[] = {
    "spaln", "sortgrcd", "makmdm", "makdbs",
    "dvn", "exinpot", "kmers", "npssm", "rdn", "utn",
};
#define N_PROGRAMS ((int)(sizeof(PROGRAMS) / sizeof(PROGRAMS[0])))

static int run_command(const char *command, char *output, size_t output_size)
{
    FILE *pipe = popen(command, "r");
    size_t used = 0;
    int status;

    if (!pipe) {
        return -1;
    }
    if (output_size > 0) {
        output[0] = '\0';
    }
    while (output_size > used + 1 &&
           fgets(output + used, (int)(output_size - used), pipe)) {
        used = strlen(output);
    }
    status = pclose(pipe);
    if (status == -1 || !WIFEXITED(status)) {
        return -1;
    }
    return WEXITSTATUS(status);
}

static int contains(const char *haystack, const char *needle)
{
    return strstr(haystack, needle) != NULL;
}

static int path_exists(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0;
}

static long file_size(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 ? (long)st.st_size : -1;
}

/* mdm_cmp is an array of 20 doubles (the PAM background composition).  The
 * exact bit pattern of the last mantissa bit is compiler/optimiser dependent
 * (the table shipped in the release archive already differs from a fresh
 * build of the very same makmdm source), so the comparison is numeric with a
 * tight tolerance instead of a byte comparison. */
#define MDM_CMP_DOUBLES 20
#define MDM_CMP_TOLERANCE 1e-9

static int doubles_close(const char *a, const char *b)
{
    FILE *fa = fopen(a, "rb");
    FILE *fb = fopen(b, "rb");
    double va[MDM_CMP_DOUBLES];
    double vb[MDM_CMP_DOUBLES];
    size_t na, nb;
    int i;
    int ok = 1;

    if (!fa || !fb) {
        if (fa) fclose(fa);
        if (fb) fclose(fb);
        return 0;
    }
    na = fread(va, sizeof(double), MDM_CMP_DOUBLES, fa);
    nb = fread(vb, sizeof(double), MDM_CMP_DOUBLES, fb);
    fclose(fa);
    fclose(fb);
    if (na != MDM_CMP_DOUBLES || nb != MDM_CMP_DOUBLES) {
        return 0;
    }
    for (i = 0; i < MDM_CMP_DOUBLES; i++) {
        double diff = va[i] - vb[i];
        double scale = vb[i] < 0 ? -vb[i] : vb[i];
        if (diff < 0) {
            diff = -diff;
        }
        if (diff > MDM_CMP_TOLERANCE * (scale > 1.0 ? scale : 1.0)) {
            fprintf(stderr, "  mdm_cmp[%d]: regenerated %.17g vs packaged %.17g\n",
                    i, va[i], vb[i]);
            ok = 0;
        }
    }
    return ok;
}

static int count_entries(const char *dir)
{
    DIR *d = opendir(dir);
    struct dirent *ent;
    int n = 0;

    if (!d) {
        return -1;
    }
    while ((ent = readdir(d)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) {
            continue;
        }
        n++;
    }
    closedir(d);
    return n;
}

/* dirname twice: <pkg>/bin/spaln -> <pkg> */
static void package_root(const char *binary, char *out, size_t out_size)
{
    char tmp[2048];
    char *slash;

    snprintf(tmp, sizeof(tmp), "%s", binary);
    slash = strrchr(tmp, '/');
    if (slash) {
        *slash = '\0';
    }
    slash = strrchr(tmp, '/');
    if (slash) {
        *slash = '\0';
    }
    snprintf(out, out_size, "%s", tmp);
}

int main(int argc, char **argv)
{
    const char *spaln = argc > 1 ? argv[1] : "spaln";
    char root[2048];
    char bindir[2048];
    char bin[2048];
    char tabledir[2048];
    char alnparam[2048];
    char mdm_mtx[2048];
    char mdm_cmp[2048];
    char tmpdir[2048];
    char cmd[4096];
    char out[OUT_SIZE];
    int passed = 0;
    int total = 10;
    int i;
    int status;

    package_root(spaln, root, sizeof(root));
    snprintf(bindir, sizeof(bindir), "%s/bin", root);
    snprintf(tabledir, sizeof(tabledir), "%s/share/spaln/table", root);
    snprintf(alnparam, sizeof(alnparam), "%s/AlnParam", tabledir);
    snprintf(mdm_mtx, sizeof(mdm_mtx), "%s/mdm_mtx", tabledir);
    snprintf(mdm_cmp, sizeof(mdm_cmp), "%s/mdm_cmp", tabledir);

    /* 1 + 2 + 3: version banner, NEON SIMD path, usage screen */
    snprintf(cmd, sizeof(cmd), "\"%s\" 2>&1", spaln);
    status = run_command(cmd, out, sizeof(out));
    if (status != -1 && contains(out, "*** SPALN") &&
        contains(out, SPALN_VERSION_LINE)) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 1: spaln banner missing '%s'\n%s\n",
                SPALN_VERSION_LINE, out);
    }
    if (contains(out, "_ARM_NEON")) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 2: spaln did not select the aarch64 NEON SIMD "
                        "path (scalar build?)\n");
    }
    if (contains(out, "Usage:")) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 3: spaln usage screen not printed\n");
    }

    /* 4: sortgrcd banner */
    snprintf(bin, sizeof(bin), "%s/sortgrcd", bindir);
    snprintf(cmd, sizeof(cmd), "\"%s\" 2>&1", bin);
    run_command(cmd, out, sizeof(out));
    if (contains(out, "sortgrcd version 2.2.2")) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 4: sortgrcd banner missing\n%s\n", out);
    }

    /* 5: makdbs banner */
    snprintf(bin, sizeof(bin), "%s/makdbs", bindir);
    snprintf(cmd, sizeof(cmd), "\"%s\" 2>&1", bin);
    run_command(cmd, out, sizeof(out));
    if (contains(out, "makdbs Version 2.0.0")) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 5: makdbs banner missing\n%s\n", out);
    }

    /* 6: every packaged executable present */
    {
        int missing = 0;
        for (i = 0; i < N_PROGRAMS; i++) {
            snprintf(bin, sizeof(bin), "%s/%s", bindir, PROGRAMS[i]);
            if (!path_exists(bin)) {
                fprintf(stderr, "FAIL 6: missing executable %s\n", bin);
                missing++;
            }
        }
        if (missing == 0) {
            passed++;
        }
    }

    /* 7: parameter table directory populated */
    {
        int n = count_entries(tabledir);
        if (n >= TABLE_MIN_ENTRIES) {
            passed++;
        } else {
            fprintf(stderr, "FAIL 7: %s holds %d entries (< %d)\n",
                    tabledir, n, TABLE_MIN_ENTRIES);
        }
    }

    /* 8: AlnParam readable through the baked-in table path */
    if (path_exists(alnparam) && file_size(alnparam) > 0) {
        passed++;
    } else {
        fprintf(stderr, "FAIL 8: %s missing or empty\n", alnparam);
    }

    /* 9 + 10: makmdm regeneration */
    snprintf(tmpdir, sizeof(tmpdir), "%s",
             getenv("TMPDIR") && *getenv("TMPDIR") ? getenv("TMPDIR") : ".");
    snprintf(cmd, sizeof(cmd), "%s/spaln-ohos-makmdm-XXXXXX", tmpdir);
    if (mkdtemp(cmd) == NULL) {
        fprintf(stderr, "FAIL 9/10: cannot create a temporary directory: %s\n",
                strerror(errno));
        printf("spaln OHOS consumer assertions: %d/%d passed\n", passed, total);
        return 1;
    }
    snprintf(bin, sizeof(bin), "%s/makmdm", bindir);
    {
        char regen_cmp[2048];
        char regen_mtx[2048];
        int rc;

        snprintf(regen_cmp, sizeof(regen_cmp), "%s/mdm_cmp", cmd);
        snprintf(regen_mtx, sizeof(regen_mtx), "%s/mdm_mtx", cmd);
        snprintf(out, sizeof(out), "\"%s\" \"%s\" >/dev/null 2>&1", bin, cmd);
        rc = run_command(out, NULL, 0);

        if (rc == 0 && path_exists(regen_cmp) && path_exists(mdm_cmp) &&
            file_size(regen_cmp) == file_size(mdm_cmp) &&
            doubles_close(regen_cmp, mdm_cmp)) {
            passed++;
        } else {
            fprintf(stderr, "FAIL 9: regenerated mdm_cmp (rc=%d) does not match "
                            "the packaged table\n", rc);
        }
        if (rc == 0 && path_exists(regen_mtx) &&
            file_size(regen_mtx) == file_size(mdm_mtx) &&
            file_size(mdm_mtx) > 0) {
            passed++;
        } else {
            fprintf(stderr, "FAIL 10: regenerated mdm_mtx geometry differs "
                            "(packaged %ld bytes)\n", file_size(mdm_mtx));
        }
    }

    printf("spaln OHOS consumer assertions: %d/%d passed\n", passed, total);
    return passed == total ? 0 : 1;
}
