/* driver_upstream.c — per-entry independent CUnit driver (r03 H1-L1)
 * Registers ONLY the suite named by argv[1] (e.g. US898, US902, US1005)
 * and runs it via the CUnit Basic interface. Returns CU error code.
 */
#include <stdio.h>
#include <string.h>
#include "CUnit/Basic.h"
#include <est.h>

extern int us898_add_suite(void);
extern int us902_add_suite(void);
extern int us1005_add_suite(void);

int main(int argc, char *argv[])
{
    int rv;
    if (argc < 2) {
        printf("usage: %s <US898|US902|US1005>\n", argv[0]);
        return 2;
    }
    /* est_apps_startup() wraps OpenSSL 1.x init removed in OpenSSL 3.x;
     * OpenSSL 3.x self-initializes, so it is skipped here. */
    if (CUE_SUCCESS != CU_initialize_registry()) {
        return CU_get_error();
    }
    if (!strcmp(argv[1], "US898"))
        rv = us898_add_suite();
    else if (!strcmp(argv[1], "US902"))
        rv = us902_add_suite();
    else if (!strcmp(argv[1], "US1005"))
        rv = us1005_add_suite();
    else {
        printf("unknown suite %s\n", argv[1]);
        CU_cleanup_registry();
        return 2;
    }
    if (rv != CUE_SUCCESS) {
        printf("\nFailed to add test suite for %s (%d)", argv[1], rv);
        CU_cleanup_registry();
        return rv;
    }
    CU_basic_set_mode(CU_BRM_VERBOSE);
    CU_basic_run_tests();
    CU_cleanup_registry();
    return CU_get_error();
}
