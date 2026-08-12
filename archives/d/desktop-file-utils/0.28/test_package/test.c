#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    /* Verify desktop-file-validate binary runs and prints version.
       Binary path passed as argv[1] (from conan package, avoids PATH dependency). */
    if (argc < 2) {
        printf("FAIL: no desktop-file-validate binary path provided\n");
        return 1;
    }
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" --version > /dev/null 2>&1", argv[1]);
    int ret = system(cmd);
    if (ret != 0) {
        printf("FAIL: desktop-file-validate --version returned %d\n", ret);
        return 1;
    }
    printf("test desktop-file-utils 0.28: OK\n");
    return 0;
}