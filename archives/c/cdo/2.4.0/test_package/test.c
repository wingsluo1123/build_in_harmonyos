#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    /* Test: run cdo --version and verify output contains version string */
    FILE *fp = popen("cdo --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run cdo --version\n");
        return 1;
    }

    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "2.4.0") != NULL || strstr(buf, "CDO") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (!found) {
        fprintf(stderr, "cdo did not report expected version info\n");
        return 1;
    }

    printf("CDO test passed: version check OK\n");
    return 0;
}