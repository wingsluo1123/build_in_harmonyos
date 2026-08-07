/* test_package source: verifies advent binary exists and runs */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    /* Find advent binary in PATH or from argument */
    const char *advent = (argc > 1) ? argv[1] : "advent";

    /* Check if the binary is accessible */
    if (access(advent, X_OK) != 0) {
        /* Try finding it via 'which' */
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "which advent 2>/dev/null");
        FILE *fp = popen(cmd, "r");
        if (fp) {
            char path[256];
            if (fgets(path, sizeof(path), fp)) {
                path[strcspn(path, "\n")] = 0;
                advent = strdup(path);
            }
            pclose(fp);
        }
    }

    /* Run advent with "quit" piped input */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "echo quit | %s 2>&1", advent);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot execute advent\n");
        return 1;
    }

    char buf[1024];
    int found_welcome = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "Adventure") || strstr(buf, "Welcome")) {
            found_welcome = 1;
        }
    }
    pclose(fp);

    if (!found_welcome) {
        fprintf(stderr, "FAIL: advent did not print welcome message\n");
        return 1;
    }

    printf("PASS: advent binary works correctly\n");
    return 0;
}
