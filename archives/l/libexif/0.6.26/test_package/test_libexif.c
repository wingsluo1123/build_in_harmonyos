#include <stdio.h>
#include <stdlib.h>
#include <libexif/exif-data.h>
#include <libexif/exif-loader.h>

int main(void) {
    /* Create an empty ExifData object to verify the library API works */
    ExifData *d = exif_data_new();
    if (!d) {
        fprintf(stderr, "exif_data_new() returned NULL\n");
        return 1;
    }
    exif_data_unref(d);

    /* Verify exif-loader API */
    ExifLoader *loader = exif_loader_new();
    if (!loader) {
        fprintf(stderr, "exif_loader_new() returned NULL\n");
        return 1;
    }
    exif_loader_free(loader);

    printf("libexif test PASSED: API calls successful\n");
    return 0;
}
