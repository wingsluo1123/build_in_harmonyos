#include <check.h>
#include <stdio.h>
#include <stdlib.h>

static void verify_check_version(void)
{
    ck_assert_int_eq(CHECK_MAJOR_VERSION, 0);
    ck_assert_int_eq(CHECK_MINOR_VERSION, 15);
}

static void verify_check_assertions(void)
{
    int value = 42;
    ck_assert_int_eq(value, 42);
    ck_assert(value > 0);
}

static int verify_check_suite_api(void)
{
    Suite *suite = suite_create("ConanCheck");
    TCase *core = tcase_create("Core");

    if (suite == NULL || core == NULL) {
        return 1;
    }

    suite_add_tcase(suite, core);
    return 0;
}

int main(void)
{
    verify_check_version();
    verify_check_assertions();

    if (verify_check_suite_api() != 0) {
        fprintf(stderr, "Failed to create Check Suite/TCase objects\n");
        return EXIT_FAILURE;
    }

    printf("Check consumer API smoke test passed\n");
    return EXIT_SUCCESS;
}
