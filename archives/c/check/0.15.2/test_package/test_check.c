#include <check.h>
#include <stdio.h>
#include <stdlib.h>

static void verify_check_version(void)
{
    if (CHECK_MAJOR_VERSION != 0 || CHECK_MINOR_VERSION != 15) {
        fprintf(stderr,
                "Unexpected Check version macros: %d.%d\n",
                CHECK_MAJOR_VERSION,
                CHECK_MINOR_VERSION);
        exit(EXIT_FAILURE);
    }
}

static void verify_plain_c_assertions(void)
{
    int value = 42;
    if (value != 42 || value <= 0) {
        fprintf(stderr, "Plain C assertion smoke check failed\n");
        exit(EXIT_FAILURE);
    }
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
    verify_plain_c_assertions();

    if (verify_check_suite_api() != 0) {
        fprintf(stderr, "Failed to create Check Suite/TCase objects\n");
        return EXIT_FAILURE;
    }

    printf("Check consumer API smoke test passed\n");
    return EXIT_SUCCESS;
}
