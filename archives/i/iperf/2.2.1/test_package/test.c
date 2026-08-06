/* test.c — iperf 2.2.1 test_package
 * Verifies the iperf binary is accessible and reports its version.
 * The actual smoke test also runs iperf --version via conanfile.py test().
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Verify iperf binary is accessible and reports version */
    int ret = system("iperf --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: iperf --version returned %d\n", ret);
        return 1;
    }
    printf("iperf test_package: binary verification OK\n");
    return 0;
}
