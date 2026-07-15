/* test.c — test_package for traceroute 2.1.6
 * Includes clif.h from the traceroute package to verify the header is installed.
 * Also links against libsupp.a to verify the library is available.
 */
#include <stdio.h>
#include "clif.h"

int main(void) {
    /* Verify clif.h is available by using its types */
    CLIF_option opts[] = {
        {"V", "version", 0, "print version and exit", 0, 0, 0, 0},
        CLIF_END_OPTION
    };
    printf("test traceroute 2.1.6: clif.h OK, %zu options\n", sizeof(opts) / sizeof(opts[0]) - 1);
    return 0;
}
