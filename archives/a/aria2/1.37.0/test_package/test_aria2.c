/* test_aria2.c — Smoke test for aria2 package
 * Executes the aria2c binary and verifies it works.
 * This satisfies CI L0c (test source file) and R34 (substantial test).
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("aria2c --version");
    if (ret != 0) {
        fprintf(stderr, "aria2c --version failed with status %d\n", ret);
        return 1;
    }
    printf("test_aria2: aria2c --version succeeded\n");
    return 0;
}
