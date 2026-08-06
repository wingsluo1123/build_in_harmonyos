/*
 * Test source for libquvi-scripts 0.9.20131130
 *
 * Verifies that the Lua scripts package is installed correctly
 * by checking the pkg-config file and version information.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int ret;

    /* Verify pkg-config can find the package */
    ret = system("pkg-config --exists libquvi-scripts-0.9");
    if (ret != 0) {
        fprintf(stderr, "FAIL: pkg-config cannot find libquvi-scripts-0.9\n");
        return 1;
    }
    printf("PASS: pkg-config found libquvi-scripts-0.9\n");

    /* Verify the version is correct */
    ret = system("pkg-config --modversion libquvi-scripts-0.9 | grep -q 0.9.20131130");
    if (ret != 0) {
        fprintf(stderr, "FAIL: version mismatch\n");
        return 1;
    }
    printf("PASS: version 0.9.20131130 verified\n");

    /* Verify the scripts directory exists */
    ret = system("pkg-config --variable=scriptsdir libquvi-scripts-0.9 | "
                 "xargs test -d");
    if (ret != 0) {
        fprintf(stderr, "FAIL: scripts directory not found\n");
        return 1;
    }
    printf("PASS: scripts directory exists\n");

    /* Verify key Lua script files exist */
    ret = system("scriptsdir=$(pkg-config --variable=scriptsdir libquvi-scripts-0.9) && "
                 "test -f \"$scriptsdir/0.9/common/quvi/const.lua\" && "
                 "test -f \"$scriptsdir/0.9/common/quvi/html.lua\" && "
                 "test -f \"$scriptsdir/0.9/common/quvi/util.lua\"");
    if (ret != 0) {
        fprintf(stderr, "FAIL: key Lua scripts not found\n");
        return 1;
    }
    printf("PASS: key Lua scripts verified\n");

    printf("\nAll libquvi-scripts tests passed.\n");
    return 0;
}
