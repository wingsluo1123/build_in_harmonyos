#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    /* Accept binary path from command line or default to "gtypist" */
    const char *gtypist_path = (argc > 1) ? argv[1] : "gtypist";
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", gtypist_path);

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: could not run %s\n", cmd);
        return 1;
    }
    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        printf("%s", buf);
        if (buf[0] != '\0' && buf[0] != '\n') found = 1;
    }
    int status = pclose(fp);
    if (status != 0 || !found) {
        fprintf(stderr, "FAIL: gtypist not working (exit=%d, path=%s)\n",
                status, gtypist_path);
        return 1;
    }
    printf("test_gnu-typist: PASS\n");
    return 0;
}