#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: test substantively depends on the tested package.
 * Runs `netdata -v` via system() and verifies the output contains
 * the expected version string. */
int main(void) {
    /* Use popen to capture netdata -v output */
    FILE *fp = popen("netdata -v 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "Failed to run netdata -v\n");
        return 1;
    }

    char buf[256];
    int ok = 0;
    if (fgets(buf, sizeof(buf), fp)) {
        /* Expected: "netdata v1.47.5" */
        if (strstr(buf, "netdata") != NULL && strstr(buf, "1.47.5") != NULL) {
            printf("netdata version check passed: %s", buf);
            ok = 1;
        } else {
            fprintf(stderr, "Unexpected output: %s", buf);
        }
    } else {
        fprintf(stderr, "No output from netdata -v\n");
    }
    pclose(fp);

    return ok ? 0 : 1;
}
