#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Test that openRTSP binary exists and runs via system() */
    int ret = system("openRTSP -h 2>/dev/null");
    if (ret == -1 || WEXITSTATUS(ret) != 0) {
        printf("test openrtsp 2026.07.08: FAILED (openRTSP -h returned %d)\n", ret);
        return 1;
    }
    printf("test openrtsp 2026.07.08: OK\n");
    return 0;
}