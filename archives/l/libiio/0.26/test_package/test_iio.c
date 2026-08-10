#include <stdio.h>
#include <iio.h>

int main(void) {
    struct iio_context *ctx = NULL;
    unsigned int major, minor;
    char git[8];
    iio_library_get_version(&major, &minor, git);
    printf("libiio version: %u.%u (git %s)\n", major, minor, git);
    printf("Backends count: %u\n", iio_get_backends_count());
    for (unsigned int i = 0; i < iio_get_backends_count(); i++) {
        const char *name = iio_get_backend(i);
        printf("  Backend %u: %s\n", i, name ? name : "()");
    }
    /* Try creating a default context (will fail gracefully if no IIO devices) */
    ctx = iio_create_default_context();
    if (ctx) {
        printf("Default context created: %s\n", iio_context_get_name(ctx));
        iio_context_destroy(ctx);
    } else {
        printf("No default context available (expected on systems without IIO devices)\n");
    }
    return 0;
}
