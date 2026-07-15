#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test: verify mini_httpd binary is installed and responds to -V flag.
 * This is a consumer-side test (R34) that actually executes the packaged binary.
 */
int main(void) {
    int ret = system("mini_httpd -V");
    if (ret != 0) {
        fprintf(stderr, "FAIL: mini_httpd -V returned %d\n", ret);
        return 1;
    }
    printf("mini_httpd binary test: PASS\n");
    return 0;
}
