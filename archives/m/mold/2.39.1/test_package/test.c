#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: Test that the mold binary is functional.
 * Calls `mold --version` and checks the exit code and output.
 * If the mold binary is broken or missing, this test will fail. */
int main(void) {
    /* Run mold --version and capture output */
    FILE *fp = popen("mold --version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "ERROR: cannot execute mold\n");
        return 1;
    }

    char buf[256];
    if (!fgets(buf, sizeof(buf), fp)) {
        pclose(fp);
        fprintf(stderr, "ERROR: mold produced no output\n");
        return 1;
    }
    int ret = pclose(fp);
    if (ret != 0) {
        fprintf(stderr, "ERROR: mold exited with status %d\n", ret);
        return 1;
    }

    /* Verify mold version string is present */
    if (strstr(buf, "mold") == NULL) {
        fprintf(stderr, "ERROR: unexpected output: %s\n", buf);
        return 1;
    }

    printf("test mold: %s", buf);
    return 0;
}
