#include <stdio.h>
#include <stdlib.h>
#include <gd.h>

int main(void) {
    /* Create a 100x100 truecolor image */
    gdImagePtr im = gdImageCreateTrueColor(100, 100);
    if (im == NULL) {
        fprintf(stderr, "FAIL: gdImageCreateTrueColor returned NULL\n");
        return 1;
    }

    /* Allocate a color (red) */
    int red = gdImageColorAllocate(im, 255, 0, 0);
    if (red < 0) {
        fprintf(stderr, "FAIL: gdImageColorAllocate returned %d\n", red);
        gdImageDestroy(im);
        return 1;
    }

    /* Draw a filled rectangle */
    gdImageFilledRectangle(im, 10, 10, 90, 90, red);

    /* Verify the pixel color at center */
    int pixel = gdImageGetPixel(im, 50, 50);
    if (pixel != red) {
        fprintf(stderr, "FAIL: pixel at (50,50) = %d, expected %d\n", pixel, red);
        gdImageDestroy(im);
        return 1;
    }

    /* Get image size */
    int sx = gdImageSX(im);
    int sy = gdImageSY(im);
    if (sx != 100 || sy != 100) {
        fprintf(stderr, "FAIL: image size %dx%d, expected 100x100\n", sx, sy);
        gdImageDestroy(im);
        return 1;
    }

    gdImageDestroy(im);
    printf("test gd 2.3.3: OK (image created, color allocated, rectangle drawn, pixel verified)\n");
    return 0;
}
