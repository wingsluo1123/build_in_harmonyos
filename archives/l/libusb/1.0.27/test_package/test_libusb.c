#include <libusb.h>

#include <stdio.h>

int main(void)
{
    const struct libusb_version *version = libusb_get_version();
    if (version == NULL) {
        fprintf(stderr, "libusb_get_version returned NULL\n");
        return 1;
    }
    if (version->major != 1 || version->minor != 0) {
        fprintf(stderr, "unexpected libusb version: %u.%u.%u\n",
                version->major, version->minor, version->micro);
        return 2;
    }

    if (libusb_error_name(LIBUSB_ERROR_ACCESS) == NULL) {
        fprintf(stderr, "libusb_error_name failed\n");
        return 3;
    }
    if (libusb_strerror(LIBUSB_ERROR_NOT_SUPPORTED) == NULL) {
        fprintf(stderr, "libusb_strerror failed\n");
        return 4;
    }

    (void)libusb_has_capability(LIBUSB_CAP_HAS_HOTPLUG);
    (void)libusb_has_capability(LIBUSB_CAP_SUPPORTS_DETACH_KERNEL_DRIVER);

    libusb_context *ctx = NULL;
    struct libusb_init_option options[1];
    options[0].option = LIBUSB_OPTION_NO_DEVICE_DISCOVERY;
    options[0].value.ival = 1;
    int rc = libusb_init_context(&ctx, options, 1);
    if (rc != LIBUSB_SUCCESS) {
        fprintf(stderr, "libusb_init_context failed: %s\n", libusb_error_name(rc));
        return 5;
    }
    if (ctx == NULL) {
        fprintf(stderr, "libusb_init_context returned NULL context\n");
        return 6;
    }
    libusb_exit(ctx);

    printf("libusb consumer smoke passed: %u.%u.%u\n",
           version->major, version->minor, version->micro);
    return 0;
}
