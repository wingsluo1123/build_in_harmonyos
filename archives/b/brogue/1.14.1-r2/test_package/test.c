#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    // Verify brogue binary exists and is executable via access()
    if (access("brogue", X_OK) != 0) {
        // Fallback: try PATH lookup
        if (system("which brogue > /dev/null 2>&1") != 0) {
            printf("FAIL: brogue binary not found\n");
            return 1;
        }
    }
    // Execute brogue to verify it actually runs
    if (system("brogue --version 2>&1 || brogue --help 2>&1 || brogue -h 2>&1") == 0) {
        printf("test brogue 1.14.1-r2: OK\n");
        return 0;
    }
    printf("FAIL: brogue binary found but execution failed\n");
    return 1;
}
