#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: test_package must substantially depend on the tested package.
     * This test verifies that the gerbv binary is present and executable. */
    int ret = system("gerbv --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: gerbv --version returned %d\n", ret);
        return 1;
    }
    printf("test gerbv 2.13.0: OK\n");
    return 0;
}
