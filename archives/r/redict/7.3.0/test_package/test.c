#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Test: verify redict-server binary exists and reports version */
    int ret = system("redict-server --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: redict-server --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: redict-server binary is functional\n");
    return 0;
}
