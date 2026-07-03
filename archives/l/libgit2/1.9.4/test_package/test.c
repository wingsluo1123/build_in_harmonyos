/*
 * test.c — libgit2 1.9.4 L1 test
 * Verifies: library init/shutdown, version info
 */
#include <git2.h>
#include <stdio.h>

int main(void) {
    int passed = 0;
    int total = 3;

    /* Test 1: Library initialization */
    int ret = git_libgit2_init();
    if (ret >= 0) {
        printf("[PASS] git_libgit2_init() returned %d\n", ret);
        passed++;
    } else {
        const git_error *err = git_error_last();
        printf("[FAIL] git_libgit2_init() failed: %s\n", err ? err->message : "unknown");
        return 1;
    }

    /* Test 2: Version info */
    int major, minor, patch;
    git_libgit2_version(&major, &minor, &patch);
    if (major == 1 && minor == 9) {
        printf("[PASS] libgit2 version: %d.%d.%d\n", major, minor, patch);
        passed++;
    } else {
        printf("[FAIL] Unexpected version: %d.%d.%d\n", major, minor, patch);
    }

    /* Test 3: Library shutdown */
    ret = git_libgit2_shutdown();
    if (ret >= 0) {
        printf("[PASS] git_libgit2_shutdown() returned %d\n", ret);
        passed++;
    } else {
        printf("[FAIL] git_libgit2_shutdown() failed\n");
    }

    printf("\nResults: %d/%d tests passed\n", passed, total);
    return (passed == total) ? 0 : 1;
}
