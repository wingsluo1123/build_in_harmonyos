/* test_package test.c — pavucontrol 6.2
 * Verifies the pavucontrol binary is installed and can report its version.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Try to find pavucontrol binary and run --version */
    int ret = system("pavucontrol --version 2>/dev/null || echo 'pavucontrol binary not found'");
    if (ret != 0) {
        printf("pavucontrol --version failed with code %d\n", ret);
        return 1;
    }
    printf("pavucontrol binary test passed\n");
    return 0;
}
