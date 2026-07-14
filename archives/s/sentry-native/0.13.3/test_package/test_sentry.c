/*
 * test_sentry.c — Simple sentry-native SDK test.
 *
 * Verifies that:
 *   1. sentry_sdk_version() returns a non-NULL version string
 *   2. sentry_options_new() creates valid options
 *   3. sentry_init() / sentry_close() lifecycle works
 */
#include <sentry.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;

    /* Test 1: SDK version string */
    const char *version = sentry_sdk_version();
    if (version == NULL || strlen(version) == 0) {
        fprintf(stderr, "FAIL: sentry_sdk_version() returned NULL or empty\n");
        failures++;
    } else {
        printf("PASS: sentry_sdk_version() = \"%s\"\n", version);
    }

    /* Test 2: Create options */
    sentry_options_t *options = sentry_options_new();
    if (options == NULL) {
        fprintf(stderr, "FAIL: sentry_options_new() returned NULL\n");
        failures++;
    } else {
        printf("PASS: sentry_options_new() succeeded\n");
    }

    /* Test 3: Init and close lifecycle (only if options is valid) */
    if (options != NULL) {
        int init_result = sentry_init(options);
        if (init_result != 0) {
            fprintf(stderr, "FAIL: sentry_init() returned %d\n", init_result);
            failures++;
        } else {
            printf("PASS: sentry_init() succeeded\n");
        }

        sentry_close();
        printf("PASS: sentry_close() succeeded\n");
    }

    if (failures > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", failures);
        return 1;
    }

    printf("\nAll sentry-native tests passed.\n");
    return 0;
}
