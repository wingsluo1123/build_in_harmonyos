#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: Execute the irssi binary to verify functionality */
    int ret = system("irssi --version");
    if (ret != 0) {
        fprintf(stderr, "irssi --version failed with exit code %d\n", ret);
        return 1;
    }
    printf("irssi test package: OK\n");
    return 0;
}
