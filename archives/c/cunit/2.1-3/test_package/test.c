/* test.c — CUnit L1 smoke test
 * Verifies that the CUnit API is available and works.
 */
#include <stdio.h>
#include <stdlib.h>
#include <CUnit/CUnit.h>
#include <CUnit/Basic.h>

static int init_suite(void) {
    return 0;
}

static int clean_suite(void) {
    return 0;
}

static void test_add(void) {
    CU_ASSERT(1 + 1 == 2);
}

static void test_multiply(void) {
    CU_ASSERT(2 * 3 == 6);
}

int main(void) {
    CU_pSuite pSuite = NULL;

    if (CUE_SUCCESS != CU_initialize_registry())
        return CU_get_error();

    pSuite = CU_add_suite("TestSuite", init_suite, clean_suite);
    if (NULL == pSuite) {
        CU_cleanup_registry();
        return CU_get_error();
    }

    if ((NULL == CU_add_test(pSuite, "test_add", test_add)) ||
        (NULL == CU_add_test(pSuite, "test_multiply", test_multiply))) {
        CU_cleanup_registry();
        return CU_get_error();
    }

    CU_basic_set_mode(CU_BRM_VERBOSE);
    if (CUE_SUCCESS != CU_basic_run_tests()) {
        printf("FAIL: CUnit framework error: %d\n", CU_get_error());
        CU_cleanup_registry();
        return CU_get_error();
    }

    unsigned int failures = CU_get_number_of_tests_failed();
    CU_cleanup_registry();

    if (failures > 0) {
        printf("FAIL: %u test(s) failed\n", failures);
        return 1;
    }

    printf("PASS: CUnit API is functional\n");
    return 0;
}