#include <stdio.h>
#include <stdlib.h>

#define STB_IMAGE_RESIZE_IMPLEMENTATION
#include "stb_image_resize2.h"

int main(void) {
    // Test basic resize API - allocate output buffer
    unsigned char input[4 * 4 * 3];  // 4x4 RGB image
    unsigned char *output;
    
    // Fill input with test data
    for (int i = 0; i < 4 * 4 * 3; i++) {
        input[i] = (unsigned char)(i % 256);
    }
    
    // Resize 4x4 to 2x2 (downsampling)
    output = stbir_resize_uint8_linear(
        input, 4, 4, 0,
        NULL, 2, 2, 0,
        STBIR_RGB
    );
    
    if (output == NULL) {
        printf("stb_image_resize2 test FAILED: resize returned NULL\n");
        return 1;
    }
    
    printf("stb_image_resize2 v2.18 test PASSED: resized 4x4 to 2x2\n");
    
    // Free allocated output
    free(output);
    
    return 0;
}
