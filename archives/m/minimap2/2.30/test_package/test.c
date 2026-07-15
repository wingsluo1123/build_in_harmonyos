#include <stdio.h>
#include <string.h>
#include "minimap.h"

/* Test that minimap2 library is correctly linked and API works.
 * This exercises the core mm_set_opt() initialization function and
 * verifies the library version matches the expected version. */
int main(void) {
    mm_idxopt_t io;
    mm_mapopt_t mo;

    /* Initialize default options (NULL preset = defaults) */
    int ret = mm_set_opt(NULL, &io, &mo);
    if (ret != 0) {
        fprintf(stderr, "FAIL: mm_set_opt returned %d\n", ret);
        return 1;
    }

    /* Verify version string matches expected */
    const char *expected = "2.30-r1287";
    if (strcmp(MM_VERSION, expected) != 0) {
        fprintf(stderr, "FAIL: version mismatch: got %s, expected %s\n",
                MM_VERSION, expected);
        return 1;
    }

    printf("minimap2 %s library test: OK\n", MM_VERSION);
    return 0;
}
