/*
 * test_package/test.c — decker 1.69 CMake/CTest smoke test.
 *
 * R34: real invocation of the installed lilt binary, not a stub.
 * Runs `lilt --version` and `lilt -e "print 1"` via system(), then
 * returns the aggregated exit code. Asserts that:
 *   - the lilt binary exists at the expected install path,
 *   - it exits 0 for --version,
 *   - it evaluates a minimal Lil script and returns 0.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int exists(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0;
}

int main(void)
{
    const char *lilt = getenv("LILT_BIN");
    if (!lilt || !*lilt)
        lilt = "/bin/lilt";

    if (!exists(lilt)) {
        fprintf(stderr, "lilt binary not found at %s\n", lilt);
        return 1;
    }

    char cmd[1024];

    /* 1. --version should exit 0 */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version > /dev/null 2>&1", lilt);
    int rc1 = system(cmd);
    if (rc1 != 0) {
        fprintf(stderr, "lilt --version failed (rc=%d)\n", rc1);
        return 2;
    }

    /* 2. evaluate a minimal Lil script that prints 1 */
    snprintf(cmd, sizeof(cmd),
             "\"%s\" -e \"print 1\" > /dev/null 2>&1", lilt);
    int rc2 = system(cmd);
    if (rc2 != 0) {
        fprintf(stderr, "lilt -e script failed (rc=%d)\n", rc2);
        return 3;
    }

    printf("test decker 1.69: OK\n");
    return 0;
}
