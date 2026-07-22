#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Test that rmlint binary is available and functional */
    int ret = system("rmlint --version");
    if (ret != 0) {
        fprintf(stderr, "FAIL: rmlint --version failed with code %d\n", ret);
        return 1;
    }

    ret = system("rmlint --help");
    if (ret != 0) {
        fprintf(stderr, "FAIL: rmlint --help failed with code %d\n", ret);
        return 1;
    }

    printf("test_rmlint: OK\n");
    return 0;
}