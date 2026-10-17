/* driver_us893.c — per-entry independent CUnit driver for US893 (r03 H1-L1)
 * Registers ONLY the US893 suite and runs it, returning CU error code.
 */
#include <stdio.h>
#include "CUnit/Basic.h"
#include <est.h>

extern int us893_add_suite(void);

int main(void)
{
    int rv;
    /* est_apps_startup() macro wraps OpenSSL 1.x init (CRYPTO_malloc_init,
     * ENGINE_load_builtin_engines, SSL_library_init) which OpenSSL 3.x
     * removed/auto-handles; OpenSSL 3.x initializes itself, so skip it. */
    if (CUE_SUCCESS != CU_initialize_registry()) {
        return CU_get_error();
    }
    rv = us893_add_suite();
    if (rv != CUE_SUCCESS) {
        printf("\nFailed to add test suite for US893 (%d)", rv);
        CU_cleanup_registry();
        return rv;
    }
    CU_basic_set_mode(CU_BRM_VERBOSE);
    CU_basic_run_tests();
    CU_cleanup_registry();
    return CU_get_error();
}
