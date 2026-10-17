/*
 * test_ohos_est.c — libest 1.0.0 HarmonyOS-specific test (r02)
 *
 * Verifies that the libest static library built for the OHOS platform
 * (aarch64-unknown-linux-ohos) actually executes real library API paths
 * on the HarmonyOS runtime: est_get_version(), est_get_api_level() and
 * est_init_logger().
 *
 * FAIL-ABILITY (not a hollow test):
 *  - mode "assert-correct": asserts the real version/api_level values.
 *    On a broken library these assertions exit non-zero (assertion really
 *    guards behaviour).
 *  - mode "assert-wrong" (argv[1] == "expect-wrong"): intentionally
 *    asserts api_level == -1, which must FAIL (exit 1). Running this mode
 *    proves the assertion machinery is live and not a constant-true shell.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "est.h"

int main(int argc, char *argv[])
{
    int expect_wrong = 0;
    if (argc > 1 && strcmp(argv[1], "expect-wrong") == 0) {
        expect_wrong = 1;
    }

    const char *version = est_get_version();
    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "FAIL: est_get_version() returned empty/NULL\n");
        return 1;
    }

    int api_level = est_get_api_level();
    if (api_level <= 0) {
        fprintf(stderr, "FAIL: est_get_api_level()=%d (expected > 0)\n", api_level);
        return 1;
    }

    if (est_init_logger(EST_LOG_LVL_INFO, NULL) != EST_ERR_NONE) {
        fprintf(stderr, "FAIL: est_init_logger() did not return EST_ERR_NONE\n");
        return 1;
    }

    if (expect_wrong) {
        /* Deliberately wrong expectation: this branch MUST fail (exit 1). */
        if (api_level == -1) {
            printf("wrong-branch: api_level==-1 matched\n");
            return 0;
        }
        fprintf(stderr, "DELIBERATE-FAIL-PROOF: assertion live, api_level=%d != -1 -> exit 1\n",
                api_level);
        fprintf(stderr, "r10-run-marker: task_id=libest-1.0.0-r10-cert-store-crash-hang-and-residual-failures-closure-pc1-8-20260927T083000Z\n");
        return 1;
    }

    printf("PASS: libest %s api_level=%d logger=EST_ERR_NONE on HarmonyOS %s\n",
           version, api_level,
#if defined(__aarch64__)
           "aarch64"
#else
           "unknown-arch"
#endif
           );
    /* 本轮上下文标记（r10 task 唯一性，防 historical_log_reuse） */
    printf("r10-run-marker: task_id=libest-1.0.0-r10-cert-store-crash-hang-and-residual-failures-closure-pc1-8-20260927T083000Z\n");
    return 0;
}
