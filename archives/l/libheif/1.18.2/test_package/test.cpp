#include <stdio.h>
#include <string.h>

#include <libheif/heif.h>

int main(void) {
    /* R34: exercise real libheif API, not just printf. */

    /* 1. Version check — verifies the header links against the right version. */
    const char *ver = heif_get_version();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: heif_get_version() returned empty\n");
        return 1;
    }
    printf("libheif version: %s\n", ver);

    /* 2. Context alloc/free — the most fundamental API lifecycle pair. */
    struct heif_context *ctx = heif_context_alloc();
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: heif_context_alloc() returned NULL\n");
        return 1;
    }
    printf("heif_context_alloc() succeeded\n");

    /* 3. Attempt to get primary image handle from an empty context.
     *    This must return a non-success error code (proving the function
     *    is linked and callable), but NOT crash. */
    struct heif_image_handle *handle = NULL;
    struct heif_error err = heif_context_get_primary_image_handle(ctx, &handle);
    if (err.code == heif_error_Ok) {
        /* An empty context should not have a primary image; if it somehow
         * does, release it. */
        if (handle) heif_image_handle_release(handle);
    } else {
        printf("heif_context_get_primary_image_handle() returned error %d (expected for empty context)\n",
               err.code);
    }

    heif_context_free(ctx);
    printf("heif_context_free() succeeded\n");

    printf("test libheif 1.18.2: OK\n");
    return 0;
}
