#include <notcurses/notcurses.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* R34: Test must actually use the notcurses API.
     * notcurses_version() returns the compiled version string.
     * This verifies: header installed, library linked, API callable. */
    const char *ver = notcurses_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: notcurses_version() returned NULL\n");
        return 1;
    }
    printf("notcurses version: %s\n", ver);
    /* Verify version contains "3.0" */
    if (strstr(ver, "3.0") == NULL) {
        fprintf(stderr, "FAIL: unexpected version %s\n", ver);
        return 1;
    }
    printf("test notcurses 3.0.17: OK\n");
    return 0;
}
