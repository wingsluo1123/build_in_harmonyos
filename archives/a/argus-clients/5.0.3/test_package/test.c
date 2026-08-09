/* test_argus_clients.c - Test source file for argus-clients test_package.
 * R34: Executes the tested package's binary via popen() and verifies output.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {
    /* Execute ra --version and verify the output contains expected version */
    FILE *fp = popen("ra --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: Cannot execute ra binary\n");
        return 1;
    }

    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "Ra Version 5.0.3") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (!found) {
        fprintf(stderr, "ERROR: ra --version did not report version 5.0.3\n");
        return 1;
    }

    printf("argus-clients test: ra --version verified OK\n");
    return 0;
}
