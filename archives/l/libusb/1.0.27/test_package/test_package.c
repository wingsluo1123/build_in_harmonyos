/* test.c — Conan L1 test for libusb 1.0.27
 *
 * Verifies: library links, version query, error-string API, and context
 * initialisation.
 *
 * HarmonyOS/OHOS note: the default initialisation path enumerates devices via
 * sysfs (/sys/bus/usb/devices/), which the sandbox denies (SELinux, errno=13),
 * and udev is absent altogether. The supported initialisation on this platform
 * is libusb_init_context() with LIBUSB_OPTION_NO_DEVICE_DISCOVERY, which is
 * what this test asserts. Device enumeration itself is therefore reported but
 * not asserted.
 */
#include <libusb.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int errors = 0;

    /* 1. Version must be reported and must be the 1.0.x series. */
    const struct libusb_version *ver = libusb_get_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: libusb_get_version() returned NULL\n");
        errors++;
    } else {
        printf("OK: libusb version = %d.%d.%d.%d%s\n",
               ver->major, ver->minor, ver->micro, ver->nano,
               ver->rc ? ver->rc : "");
        if (ver->major != 1 || ver->minor != 0) {
            fprintf(stderr, "FAIL: unexpected version %d.%d (want 1.0.x)\n",
                    ver->major, ver->minor);
            errors++;
        }
    }

    /* 2. Error-name table must be linked in and correct. */
    const char *name = libusb_error_name(LIBUSB_ERROR_NO_DEVICE);
    if (name == NULL || strcmp(name, "LIBUSB_ERROR_NO_DEVICE") != 0) {
        fprintf(stderr, "FAIL: libusb_error_name(LIBUSB_ERROR_NO_DEVICE) = %s\n",
                name ? name : "(null)");
        errors++;
    } else {
        printf("OK: libusb_error_name() = %s\n", name);
    }

    /* 3. Human-readable strerror must return a non-empty string. */
    const char *msg = libusb_strerror(LIBUSB_ERROR_TIMEOUT);
    if (msg == NULL || msg[0] == '\0') {
        fprintf(stderr, "FAIL: libusb_strerror() is empty\n");
        errors++;
    } else {
        printf("OK: libusb_strerror(LIBUSB_ERROR_TIMEOUT) = %s\n", msg);
    }

    /* 4. Context initialisation without device discovery (OHOS-supported path). */
    libusb_context *ctx = NULL;
    struct libusb_init_option opts[1];
    memset(opts, 0, sizeof(opts));
    opts[0].option = LIBUSB_OPTION_NO_DEVICE_DISCOVERY;

    int rc = libusb_init_context(&ctx, opts, 1);
    if (rc != LIBUSB_SUCCESS || ctx == NULL) {
        fprintf(stderr, "FAIL: libusb_init_context(NO_DEVICE_DISCOVERY) = %d (%s)\n",
                rc, libusb_error_name(rc));
        errors++;
    } else {
        printf("OK: libusb_init_context() with NO_DEVICE_DISCOVERY succeeded\n");

        /* 5. Informational only: with discovery disabled an empty list is
         *    the expected outcome; a negative return is tolerated because it
         *    reflects platform sandbox policy, not a library defect. */
        libusb_device **list = NULL;
        ssize_t n = libusb_get_device_list(ctx, &list);
        if (n >= 0) {
            printf("INFO: libusb_get_device_list() reported %ld device(s)\n", (long)n);
            libusb_free_device_list(list, 1);
        } else {
            printf("INFO: libusb_get_device_list() = %ld (%s) - expected on OHOS\n",
                   (long)n, libusb_error_name((int)n));
        }

        libusb_exit(ctx);
        printf("OK: libusb_exit() completed\n");
    }

    if (errors > 0) {
        fprintf(stderr, "FAILED with %d error(s)\n", errors);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
