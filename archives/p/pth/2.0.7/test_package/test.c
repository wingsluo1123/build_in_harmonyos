#include <stdio.h>
#include <pth.h>

int main(void) {
    long ver = pth_version();
    printf("pth version: %ld (%s)\n", ver, PTH_VERSION_STR);
    if (ver > 0) {
        printf("test pth 2.0.7: OK\n");
        return 0;
    }
    printf("test pth 2.0.7: FAIL\n");
    return 1;
}
