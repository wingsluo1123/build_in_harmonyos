/*
 * test_searchd_help.c — Manticore test_package
 *
 * Verifies the manticore searchd binary is installed and runnable.
 * Calls searchd --help and checks the output contains expected text.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Construct the path to searchd binary */
    const char *bindir = getenv("CONAN_BIN_PATHS_MANTICORE");
    char cmd[4096];

    if (bindir) {
        snprintf(cmd, sizeof(cmd), "%s/searchd --help 2>&1", bindir);
    } else {
        /* Fallback: assume searchd is in PATH */
        snprintf(cmd, sizeof(cmd), "searchd --help 2>&1");
    }

    /* Run searchd --help and capture output */
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run searchd --help\n");
        return 1;
    }

    /* Read output and check for expected content */
    char buf[1024];
    int found_manticore = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        /* searchd --help should mention "Manticore" in the help text */
        if (strstr(buf, "Manticore") != NULL || strstr(buf, "manticore") != NULL) {
            found_manticore = 1;
            break;
        }
    }
    pclose(fp);

    if (!found_manticore) {
        fprintf(stderr, "searchd --help did not produce expected output\n");
        return 1;
    }

    printf("searchd --help: OK — Manticore binary is working\n");
    return 0;
}
