/* Consumer smoke test for libmtp 1.1.21.
 * Links against the installed libmtp (+ transitive libusb-1.0 via the
 * conan graph) and exercises the public API:
 *   - LIBMTP_VERSION_STRING compile/link sanity
 *   - LIBMTP_Detect_Raw_Devices(): the full USB enumeration entry point.
 *     On the OHOS build host there is no MTP device (and possibly no
 *     usbfs), so both "no device attached" and "connecting" outcomes are
 *     acceptable; only an unexpected error class is a failure.
 */
#include <libmtp.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    /* 1) version string must match the adapted version */
    if (strcmp(LIBMTP_VERSION_STRING, "1.1.21") != 0) {
        fprintf(stderr, "unexpected LIBMTP_VERSION_STRING: %s\n",
                LIBMTP_VERSION_STRING);
        return 1;
    }

    /* 2) device detection must run to completion */
    LIBMTP_raw_device_t *rawdevices = NULL;
    int numrawdevices = 0;
    LIBMTP_error_number_t err = LIBMTP_Detect_Raw_Devices(&rawdevices, &numrawdevices);
    if (err != LIBMTP_ERROR_NONE
        && err != LIBMTP_ERROR_NO_DEVICE_ATTACHED
        && err != LIBMTP_ERROR_CONNECTING) {
        fprintf(stderr, "unexpected detect error class: %d\n", (int)err);
        return 2;
    }
    if (err == LIBMTP_ERROR_NONE && numrawdevices < 0) {
        fprintf(stderr, "inconsistent detect result: err=%d num=%d\n",
                (int)err, numrawdevices);
        return 3;
    }
    free(rawdevices);

    printf("libmtp consumer smoke passed: %s (detect err=%d, num=%d)\n",
           LIBMTP_VERSION_STRING, (int)err, numrawdevices);
    return 0;
}
