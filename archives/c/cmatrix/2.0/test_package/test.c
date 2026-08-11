/*
 * test.c - cmatrix 2.0 consumer smoke test
 *
 * Calls the cmatrix binary via popen() to verify:
 *   1. -V prints version "CMatrix version 2.0"
 *   2. -V exits with code 0
 *   3. -h prints usage "Usage: cmatrix"
 *   4. -V mentions email and web URL
 *   5. -C <invalid> reports "Invalid color selection"
 *   6. -s screensaver mode emits terminal escape sequences
 *
 * R34: test substantively depends on the tested package binary.
 * The cmatrix binary path is read from CMATRIX_BIN env var (set by conanfile.py).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int passed = 0;
static int failed = 0;

static void check(int ok, const char *desc) {
    if (ok) {
        printf("PASS: %s\n", desc);
        passed++;
    } else {
        printf("FAIL: %s\n", desc);
        failed++;
    }
}

static int run_capture(const char *cmd, char *buf, size_t bufsz) {
    char full[512];
    snprintf(full, sizeof(full), "%s 2>&1", cmd);
    FILE *fp = popen(full, "r");
    if (!fp) return -1;
    size_t n = fread(buf, 1, bufsz - 1, fp);
    buf[n] = 0;
    return pclose(fp);
}

int main(void) {
    const char *cmatrix = getenv("CMATRIX_BIN");
    if (!cmatrix) cmatrix = "cmatrix";

    char cmd[512];
    char buf[8192];
    int rc;

    snprintf(cmd, sizeof(cmd), "%s -V", cmatrix);
    rc = run_capture(cmd, buf, sizeof(buf));
    check(strstr(buf, "CMatrix version 2.0") != NULL,
          "cmatrix -V prints CMatrix version 2.0");
    check(rc == 0, "cmatrix -V exits with code 0");

    snprintf(cmd, sizeof(cmd), "%s -h", cmatrix);
    rc = run_capture(cmd, buf, sizeof(buf));
    check(strstr(buf, "Usage: cmatrix") != NULL,
          "cmatrix -h prints Usage: cmatrix");

    snprintf(cmd, sizeof(cmd), "%s -V", cmatrix);
    run_capture(cmd, buf, sizeof(buf));
    check(strstr(buf, "abishekvashok@gmail.com") != NULL &&
          strstr(buf, "github.com/abishekvashok/cmatrix") != NULL,
          "cmatrix -V mentions email and web URL");

    snprintf(cmd, sizeof(cmd), "%s -C invalidcolor", cmatrix);
    run_capture(cmd, buf, sizeof(buf));
    check(strstr(buf, "Invalid color selection") != NULL,
          "cmatrix -C invalidcolor reports Invalid color selection");

    snprintf(cmd, sizeof(cmd),
             "timeout 1 %s -s -u 1 2>&1 | head -c 200", cmatrix);
    rc = run_capture(cmd, buf, sizeof(buf));
    int has_esc = (strchr(buf, 0x1b) != NULL);
    check(has_esc,
          "cmatrix -s screensaver mode emits terminal escape sequences");

    printf("\n=== Results: %d passed, %d failed (total %d) ===\n",
           passed, failed, passed + failed);
    return failed > 0 ? 1 : 0;
}
