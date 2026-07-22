#include <stdlib.h>
#include <stdio.h>

int main() {
    // Verify brogue binary is findable via PATH
    int ret = system("which brogue > /dev/null 2>&1");
    if (ret != 0) {
        printf("FAIL: brogue binary not found in PATH\n");
        return 1;
    }
    // Try running brogue - if ALL attempts fail, binary is likely broken
    ret = system("brogue --version > /dev/null 2>&1");
    if (ret == 0) {
        printf("test brogue 1.14.1-r2: OK\n");
        return 0;
    }
    ret = system("brogue --help > /dev/null 2>&1");
    if (ret == 0) {
        printf("test brogue 1.14.1-r2: OK\n");
        return 0;
    }
    // Binary exists but execution failed - likely broken or missing deps
    printf("FAIL: brogue binary found but execution failed\n");
    return 1;
}
