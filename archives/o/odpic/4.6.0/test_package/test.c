/*
 * Consumer test for the packaged odpic 4.6.0 (ODPI-C) on HarmonyOS PC.
 *
 * This is a real consumer: it links against the packaged shared library
 * (dpi::odpic), includes the packaged header and calls the packaged API.
 * It never needs an Oracle Client library, because ODPI-C dlopen()s the
 * client at run time: with the client absent the call fails with a
 * well-formed DPI- error produced *inside* the packaged library, which is
 * itself the proof that the library was loaded and executed on OHOS.
 *
 * Assertions:
 *   A1  packaged header DPI_VERSION_NUMBER == 40600 (4.6.0)
 *   A2  packaged header DPI_VERSION_STRING == "4.6.0"
 *   A3  dpiContext_createWithParams() returns DPI_SUCCESS (client present)
 *       or DPI_FAILURE (client absent) -- no third outcome is acceptable
 *   A4  on the DPI_FAILURE path the library reports its own DPI- diagnostic
 *       (non-zero message, "DPI-" prefix)
 *   A5  on the DPI_FAILURE path the diagnostic names the Oracle Client,
 *       i.e. the failure is the documented missing-client path and not an
 *       unrelated aberration
 */
#include <stdio.h>
#include <string.h>

#include <dpi.h>

static int checks_passed = 0;
static int checks_failed = 0;

static void report(int number, const char *title, int ok, const char *detail)
{
    printf("%s %d: %s -- %s\n", ok ? "PASS" : "FAIL", number, title, detail);
    if (ok)
        checks_passed++;
    else
        checks_failed++;
}

int main(void)
{
    dpiContext *context = NULL;
    dpiErrorInfo errorInfo;
    int rc;
    char detail[512];

    printf("odpic 4.6.0 consumer test\n");

    /* A1: header version number */
    snprintf(detail, sizeof(detail), "DPI_VERSION_NUMBER=%d", DPI_VERSION_NUMBER);
    report(1, "packaged header version number is 40600",
           DPI_VERSION_NUMBER == 40600, detail);

    /* A2: header version string */
    report(2, "packaged header version string is 4.6.0",
           strcmp(DPI_VERSION_STRING, "4.6.0") == 0, DPI_VERSION_STRING);

    /* A3: context creation through the packaged library */
    memset(&errorInfo, 0, sizeof(errorInfo));
    rc = dpiContext_createWithParams(DPI_MAJOR_VERSION, DPI_MINOR_VERSION,
            NULL, &context, &errorInfo);
    if (rc == DPI_SUCCESS) {
        report(3, "dpiContext_createWithParams() succeeded", 1,
               "Oracle Client present: full ODPI-C path exercised");
        dpiContext_destroy(context);
        report(4, "DPI- diagnostic path", 1,
               "not applicable: context created successfully");
        report(5, "missing-client diagnosis", 1,
               "not applicable: context created successfully");
    } else {
        snprintf(detail, sizeof(detail),
                 "rc=%d (expected %d for a missing Oracle Client)", rc,
                 DPI_FAILURE);
        report(3, "dpiContext_createWithParams() exercised",
               rc == DPI_FAILURE, detail);

        snprintf(detail, sizeof(detail), "messageLength=%u", errorInfo.messageLength);
        report(4, "packaged library produced its own DPI- diagnostic",
               errorInfo.message != NULL && errorInfo.messageLength > 0 &&
               strncmp(errorInfo.message, "DPI-", 4) == 0, detail);

        report(5, "diagnostic is the documented missing-client path",
               errorInfo.message != NULL &&
               strstr(errorInfo.message, "Oracle Client") != NULL,
               errorInfo.message != NULL ? errorInfo.message : "<null>");
    }

    printf("RESULT: %d/%d assertions passed\n",
           checks_passed, checks_passed + checks_failed);
    if (checks_failed != 0) {
        printf("FAIL: %d assertion(s) failed\n", checks_failed);
        return 1;
    }
    printf("PASS: all %d consumer assertions passed\n", checks_passed);
    return 0;
}
