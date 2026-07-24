#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {
    // Get binary path from test argument, or search PATH as fallback
    const char *brogue_bin = "brogue";
    if (argc > 1)
        brogue_bin = argv[1];

    // Verify brogue binary exists and is executable via access()
    if (access(brogue_bin, X_OK) != 0) {
        // Fallback: try PATH lookup
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "which %s > /dev/null 2>&1", brogue_bin);
        if (system(cmd) != 0) {
            printf("FAIL: brogue binary '%s' not found\n", brogue_bin);
            return 1;
        }
    }

    printf("test brogue 1.14.1-r2: OK\n");
    return 0;
}
