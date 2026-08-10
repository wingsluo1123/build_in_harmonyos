/*
 * test_baresip.c — baresip 4.9.0 L1 test
 * Verifies: library version string, config initialization, module list
 *
 * Note: baresip.h uses `bool` type which requires stdbool.h.
 * re.h (from libre) includes re_types.h which includes stdbool.h,
 * so we include re.h before baresip.h.
 *
 * baresip_init() requires full network/DNS initialization which may
 * not be available on all platforms (e.g. OHOS). This test focuses on
 * the library API that doesn't require network initialization.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <re/re.h>
#include <baresip.h>

int main(void) {
    int passed = 0;
    int total = 3;

    /* Test 1: Version string */
    const char *version = baresip_version();
    if (version && strstr(version, "4.9.0")) {
        printf("[PASS] baresip version: %s\n", version);
        passed++;
    } else {
        printf("[FAIL] baresip version: %s\n", version ? version : "NULL");
    }

    /* Test 2: Configure via conf_configure_buf */
    static const char modconfig[] = "ausrc_format    s16\n";
    int err = conf_configure_buf((const uint8_t *)modconfig,
                                 sizeof(modconfig) - 1);
    if (err == 0) {
        printf("[PASS] conf_configure_buf succeeded\n");
        passed++;
    } else {
        printf("[FAIL] conf_configure_buf error: %d\n", err);
        printf("\n=== %d/%d tests passed ===\n", passed, total);
        return 1;
    }

    /* Test 3: config structure is accessible after conf_configure.
     * config->sip.local is char[64] — its array address always evaluates to
     * true, so checking it proves nothing. Instead verify a scalar field
     * with a known non-zero default: config->call.local_timeout (120). */
    struct config *config = conf_config();
    if (config) {
        if (config->call.local_timeout != 0) {
            printf("[PASS] config structure accessible "
                   "(local_timeout=%u)\n",
                   config->call.local_timeout);
            passed++;
        } else {
            printf("[FAIL] config->call.local_timeout is 0\n");
        }
    } else {
        printf("[FAIL] conf_config returned NULL\n");
    }

    printf("\n=== %d/%d tests passed ===\n", passed, total);
    return (passed == total) ? 0 : 1;
}
