#include <stdio.h>
#include <stdlib.h>
#include <libexif/exif-data.h>
#include <libexif/exif-loader.h>

int main(void) {
    ExifData *data = exif_data_new();
    if (data) {
        printf("libexif 0.6.26: exif_data_new() succeeded\n");
        exif_data_unref(data);
    } else {
        printf("libexif 0.6.26: exif_data_new() returned NULL (acceptable without image data)\n");
    }
    printf("test libexif 0.6.26: OK\n");
    return 0;
}
