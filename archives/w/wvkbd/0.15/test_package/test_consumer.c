/* SPDX-License-Identifier: GPL-3.0-only */
#include "core_cases.h"
#include <stdio.h>

/* Numeric bridge for the separate test HAP. Execute these exact installed
 * cases on the device, without parsing strings or substituting a host result. */
int wvkbd_test_consumer_results(int *results, size_t count)
{
    if (!results || count != wvkbd_test_case_count) return -1;
    int failed = 0;
    for (size_t i = 0; i < count; ++i) {
        results[i] = wvkbd_test_cases[i].run() == 0 ? 1 : 0;
        failed |= results[i] == 0;
    }
    return failed;
}

/* Report contract: C01..C04 are four uniquely identified core test items.
 * Each line is Cnn=pass or Cnn=fail; only a complete report may return 0.
 * The caller owns the buffer. No device IDs or real user input are recorded.
 * Return -1 for an invalid/undersized report, 1 for a failed API check. */
int wvkbd_test_consumer_run(char *report, size_t report_capacity)
{
    size_t used = 0;
    int failed = 0;
    if (!report || report_capacity == 0) return -1;
    report[0] = '\0';
    for (size_t i = 0; i < wvkbd_test_case_count; ++i) {
        int result = wvkbd_test_cases[i].run();
        int count = snprintf(report + used, report_capacity - used, "%s=%s\n",
                             wvkbd_test_cases[i].id, result ? "fail" : "pass");
        if (count < 0 || (size_t)count >= report_capacity - used) return -1;
        used += (size_t)count;
        failed |= result != 0;
    }
    return failed;
}

#ifdef WVKBD_TEST_CONSUMER_MAIN
int main(void)
{
    char report[256];
    int result = wvkbd_test_consumer_run(report, sizeof report);
    fputs(report, stdout);
    return result == 0 ? 0 : 1;
}
#endif
