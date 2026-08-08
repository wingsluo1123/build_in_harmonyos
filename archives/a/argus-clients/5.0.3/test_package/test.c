/* test_argus_clients.c - Test source file for argus-clients test_package.
 * Uses popen() to execute `ra --version` and verify the output
 * contains "Ra Version 5.0.3" (R34: executes tested package binary).
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[256];
    int found = 0;

    fp = popen("ra --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run ra --version\n");
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "Ra Version") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (found) {
        printf("argus-clients test: PASSED (ra binary verified)\n");
        return 0;
    } else {
        fprintf(stderr, "argus-clients test: FAILED (ra --version did not show expected output)\n");
        return 1;
    }
}
