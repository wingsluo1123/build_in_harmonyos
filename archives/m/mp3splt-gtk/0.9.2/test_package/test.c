// test.c — Test that mp3splt-gtk binary can be found and executed
// R34: Tests the actual package binary, not just a dependency
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]) {
    // Try to find the mp3splt-gtk binary
    const char *binary = getenv("MP3SPLT_GTK_BINARY");
    if (!binary) {
        // Try common paths
        const char *paths[] = {
            "/usr/local/bin/mp3splt-gtk",
            "/usr/bin/mp3splt-gtk",
            NULL
        };
        for (int i = 0; paths[i]; i++) {
            if (access(paths[i], X_OK) == 0) {
                binary = paths[i];
                break;
            }
        }
    }

    if (!binary) {
        fprintf(stderr, "mp3splt-gtk binary not found\n");
        return 1;
    }

    // Execute mp3splt-gtk --version to verify the binary works
    // Using --version which doesn't require a display server
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", binary);

    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "mp3splt-gtk --version failed with code %d\n", ret);
        return 1;
    }

    printf("mp3splt-gtk binary verified successfully\n");
    return 0;
}
