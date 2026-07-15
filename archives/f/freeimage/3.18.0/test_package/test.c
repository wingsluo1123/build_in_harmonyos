#include <stdio.h>
#include <FreeImage.h>

int main(void) {
    /* Test 1: Library initialization and version query */
    FreeImage_Initialise(FALSE);
    const char *version = FreeImage_GetVersion();
    printf("FreeImage version: %s\n", version);

    /* Test 2: Create a 2x2 24-bit image */
    FIBITMAP *dib = FreeImage_Allocate(2, 2, 24, 0xFF0000, 0x00FF00, 0x0000FF);
    if (!dib) {
        fprintf(stderr, "Failed to allocate image\n");
        FreeImage_DeInitialise();
        return 1;
    }

    /* Test 3: Set a red pixel.
     * RGBQUAD layout: {rgbBlue, rgbGreen, rgbRed, rgbReserved}
     * For red: Blue=0, Green=0, Red=255 */
    RGBQUAD color = {0, 0, 255, 0};  /* Red */
    FreeImage_SetPixelColor(dib, 0, 0, &color);

    /* Test 4: Get pixel back and verify */
    RGBQUAD read_color;
    FreeImage_GetPixelColor(dib, 0, 0, &read_color);
    if (read_color.rgbRed != 255 || read_color.rgbGreen != 0 || read_color.rgbBlue != 0) {
        fprintf(stderr, "Pixel color mismatch: R=%u G=%u B=%u\n",
                read_color.rgbRed, read_color.rgbGreen, read_color.rgbBlue);
        FreeImage_Unload(dib);
        FreeImage_DeInitialise();
        return 1;
    }

    /* Test 5: Check image dimensions */
    unsigned width = FreeImage_GetWidth(dib);
    unsigned height = FreeImage_GetHeight(dib);
    if (width != 2 || height != 2) {
        fprintf(stderr, "Image dimensions mismatch: %ux%u\n", width, height);
        FreeImage_Unload(dib);
        FreeImage_DeInitialise();
        return 1;
    }

    printf("All tests passed (version=%s, %ux%u)\n", version, width, height);

    FreeImage_Unload(dib);
    FreeImage_DeInitialise();
    return 0;
}
