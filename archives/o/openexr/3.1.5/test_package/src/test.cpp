/*
 * test.cpp -- Consumer test for openexr Conan package
 *
 * Exercises the OpenEXR API:
 * 1. Creates an Imf::Header object and verifies data window dimensions
 * 2. Uses Imf::Array2D template to verify array API availability
 */
#include <OpenEXR/ImfHeader.h>
#include <OpenEXR/ImfArray.h>

#include <cstdio>

int main()
{
    /* Create an OpenEXR header with a 64x64 data window */
    Imf::Header header(64, 64);

    /* Verify the data window dimensions */
    if (header.dataWindow().min.x != 0 || header.dataWindow().min.y != 0) {
        fprintf(stderr, "FAIL: unexpected data window min\n");
        return 1;
    }
    if (header.dataWindow().max.x != 63 || header.dataWindow().max.y != 63) {
        fprintf(stderr, "FAIL: unexpected data window max\n");
        return 1;
    }

    /* Use Imf::Array2D to verify the array template is available */
    Imf::Array2D<float> pixels(4, 4);
    pixels[0][0] = 1.0f;
    if (pixels[0][0] != 1.0f) {
        fprintf(stderr, "FAIL: Array2D value mismatch\n");
        return 1;
    }

    printf("OpenEXR header and array API verified.\n");
    return 0;
}
