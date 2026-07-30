#include <check.h>
#include <stdio.h>
#include <stdlib.h>

START_TEST(test_check_version)
{
    ck_assert_int_eq(CHECK_MAJOR_VERSION, 0);
    ck_assert_int_eq(CHECK_MINOR_VERSION, 15);
}
END_TEST

START_TEST(test_check_assert)
{
    int value = 42;
    ck_assert_int_eq(value, 42);
    ck_assert(value > 0);
}
END_TEST

static Suite *check_conan_suite(void)
{
    Suite *suite = suite_create("ConanCheck");
    TCase *core = tcase_create("Core");

    tcase_add_test(core, test_check_version);
    tcase_add_test(core, test_check_assert);
    suite_add_tcase(suite, core);

    return suite;
}

int main(void)
{
    Suite *suite = check_conan_suite();
    SRunner *runner = srunner_create(suite);
    srunner_set_fork_status(runner, CK_NOFORK);
    srunner_run_all(runner, CK_NORMAL);
    const int failed = srunner_ntests_failed(runner);
    srunner_free(runner);

    printf("Check consumer tests failed: %d\n", failed);
    return failed == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
