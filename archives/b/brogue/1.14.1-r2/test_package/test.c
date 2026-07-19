#include <stdlib.h>
#include <stdio.h>

int main() {
    int ret = system("brogue --version > /dev/null 2>&1");
    if (ret != 0) {
        ret = system("brogue --help > /dev/null 2>&1");
    }
    if (ret != 0) {
        printf("FAIL: brogue binary not executable\n");
        return 1;
    }
    printf("test brogue 1.14.1-r2: OK\n");
    return 0;
}
