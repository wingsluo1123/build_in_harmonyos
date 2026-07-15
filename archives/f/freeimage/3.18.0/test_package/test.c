#include <stdio.h>
#include <FreeImage.h>

int main(void) {
    /* Test 1: Library initialization */
    FreeImage_Initialise(FALSE);

    /* Test 2: Version query */
    const char *version = FreeImage_GetVersion();
    if (!version || version[0] == '\0') {
        fprintf(stderr, "Failed to get FreeImage version\n");
        FreeImage_DeInitialise();
        return 1;
    }
    printf("FreeImage version: %s\n", version);

    /* Test 3: Create a 2x2 24-bit image */
    FIBITMAP *dib = FreeImage_Allocate(2, 2, 24, 0xFF0000, 0x00FF00, 0x0000FF);
    if (!dib) {
        fprintf(stderr, "Failed to allocate image\n");
        FreeImage_DeInitialise();
        return 1;
    }

    /* Test 4: Set a red pixel (RGBQUAD: {Blue, Green, Red, Reserved}) */
    RGBQUAD color = {0, 0, 255, 0};
    FreeImage_SetPixelColor(dib, 0, 0, &color);

    /* Test 5: Get pixel back and verify */
    RGBQUAD read_color;
    FreeImage_GetPixelColor(dib, 0, 0, &read_color);
    if (read_color.rgbRed != 255 || read_color.rgbGreen != 0 || read_color.rgbBlue != 0) {
        fprintf(stderr, "Pixel color mismatch: R=%u G=%u B=%u\n",
                read_color.rgbRed, read_color.rgbGreen, read_color.rgbBlue);
        FreeImage_Unload(dib);
        FreeImage_DeInitialise();
        return 1;
    }

    /* Test 6: Check dimensions */
    unsigned width = FreeImage_GetWidth(dib);
    unsigned height = FreeImage_GetHeight(dib);
    if (width != 2 || height != 2) {
        fprintf(stderr, "Dimensions mismatch: %ux%u\n", width, height);
        FreeImage_Unload(dib);
        FreeImage_DeInitialise();
        return 1;
    }

    printf("All tests passed (version=%s, %ux%u)\n", version, width, height);

    FreeImage_Unload(dib);
    FreeImage_DeInitialise();
    return 0;
}
