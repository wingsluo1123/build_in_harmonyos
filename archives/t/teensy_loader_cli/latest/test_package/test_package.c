/* L0/L1 test for the packaged teensy_loader_cli.
 *
 * 1) --list-mcus            : hardware independent CLI output check.
 * 2) --mcu=atmega32u4 -b    : exercises the real USB backend.  The -b (boot
 *                             only) flag skips the firmware file and goes
 *                             straight to teensy_open(), which performs a real
 *                             libusb_init() plus USB device enumeration.  With
 *                             no Teensy attached the tool must fail loudly
 *                             instead of silently reporting success.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

/* Runs cmd, captures up to sizeof(buf)-1 bytes of output.
 * Returns the exit code, or -1 when the command could not be run. */
static int run_capture(const char *cmd, char *buf, size_t buflen) {
    FILE *fp;
    size_t n;
    int rc;

    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp) return -1;
    n = fread(buf, 1, buflen - 1, fp);
    buf[n] = '\0';
    rc = pclose(fp);
    if (rc == -1) return -1;
    return WIFEXITED(rc) ? WEXITSTATUS(rc) : -1;
}

static int check_list_mcus(void) {
    char buf[4096];
    int code = run_capture("teensy_loader_cli --list-mcus 2>&1", buf, sizeof(buf));

    if (code == -1) {
        fprintf(stderr, "FAIL: could not run teensy_loader_cli --list-mcus\n");
        return 1;
    }
    /* Upstream exits with status 1 right after printing the MCU list. */
    if (code != 1) {
        fprintf(stderr, "FAIL: --list-mcus exit code %d, expected 1\n", code);
        return 1;
    }
    if (!strstr(buf, "Supported MCUs are:") ||
        !strstr(buf, "atmega32u4") ||
        !strstr(buf, "at90usb1286")) {
        fprintf(stderr, "FAIL: --list-mcus output missing MCU list\n");
        return 1;
    }
    return 0;
}

static int check_usb_enumeration(void) {
    char buf[4096];
    int code = run_capture("teensy_loader_cli --mcu=atmega32u4 -b 2>&1",
                           buf, sizeof(buf));

    if (code == -1) {
        fprintf(stderr, "FAIL: could not run the USB enumeration path\n");
        return 1;
    }
    if (code == 0) {
        /* A Teensy is actually attached and the USB path completed. */
        return 0;
    }
    /* No device attached: enumeration must have run through libusb and the
     * tool must report the failure explicitly rather than exiting silently
     * or claiming success. */
    if (!strstr(buf, "Unable to open device")) {
        fprintf(stderr,
                "FAIL: USB path exited %d without the expected "
                "\"Unable to open device\" diagnostic; output was:\n%s\n",
                code, buf);
        return 1;
    }
    return 0;
}

int main(void) {
    if (check_list_mcus() != 0) return 1;
    if (check_usb_enumeration() != 0) return 1;
    printf("teensy_loader_cli test_package: OK\n");
    return 0;
}
