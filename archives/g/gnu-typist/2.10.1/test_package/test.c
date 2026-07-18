#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Run gtypist binary to verify the package was installed correctly */
    FILE *fp = popen("gtypist --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: could not run gtypist\n");
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
        fprintf(stderr, "FAIL: gtypist not working (exit=%d)\n", status);
        return 1;
    }
    printf("test_gnu-typist: PASS\n");
    return 0;
}