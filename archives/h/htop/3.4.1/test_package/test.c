#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Test that htop binary is accessible and runs --version */
    int rc = system("htop --version > /dev/null 2>&1");
    if (rc == 0) {
        printf("test htop 3.4.1: htop --version OK\n");
        return 0;
    } else {
        printf("test htop 3.4.1: htop --version FAILED\n");
        return 1;
    }
}
