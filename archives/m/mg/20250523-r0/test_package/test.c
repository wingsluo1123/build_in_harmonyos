#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret;
    /* Test mg --version to verify the binary works */
    ret = system("mg --version");
    if (ret != 0) {
        fprintf(stderr, "FAIL: mg --version returned %d\n", ret);
        return 1;
    }
    printf("test mg 20250523-r0: OK\n");
    return 0;
}