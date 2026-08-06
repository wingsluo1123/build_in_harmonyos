#include <stdio.h>
#include <stdlib.h>

int main() {
    /* Test that thrift1 compiler is available and functional */
    int ret = system("thrift1 --version > /dev/null 2>&1");
    if (ret != 0) {
        printf("FAIL: thrift1 --version failed\n");
        return 1;
    }
    printf("OK: thrift1 compiler is functional\n");
    return 0;
}
