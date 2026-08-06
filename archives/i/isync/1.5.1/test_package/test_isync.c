/*
 * test_isync.c — Test package for isync 1.5.1
 *
 * isync is a command-line tool (mbsync), not a library.
 * This test verifies the installed mbsync binary works by
 * executing it with --version and checking the exit code.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Run mbsync --version to verify the binary is functional */
    int ret = system("mbsync --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: mbsync --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: mbsync binary is functional\n");
    return 0;
}
