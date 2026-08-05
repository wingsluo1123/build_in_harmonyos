/* test_package/test.c — Blend2D C API smoke test (R34: calls real API)
 *
 * Creates a small image, renders a filled circle, and verifies success.
 * Uses the blend2d C API (BLResult, BLImageCore, BLContextCore).
 * Based on the official bl_sample_capi.c sample.
 */
#include <blend2d/blend2d.h>
#include <stdio.h>

int main(void) {
    BLResult r;
    BLImageCore img;
    BLContextCore ctx;

    /* Create a 128x128 PRGB32 image */
    r = bl_image_init_as(&img, 128, 128, BL_FORMAT_PRGB32);
    if (r != BL_SUCCESS) {
        fprintf(stderr, "bl_image_init_as failed: %u\n", r);
        return 1;
    }

    /* Create a rendering context */
    r = bl_context_init_as(&ctx, &img, NULL);
    if (r != BL_SUCCESS) {
        fprintf(stderr, "bl_context_init_as failed: %u\n", r);
        bl_image_destroy(&img);
        return 1;
    }

    /* Clear the image */
    bl_context_clear_all(&ctx);

    /* Fill a circle with a radial gradient (same pattern as official sample) */
    BLGradientCore radial;
    BLRadialGradientValues radial_values = { 64, 64, 64, 64, 48, 0 };
    bl_gradient_init_as(&radial, BL_GRADIENT_TYPE_RADIAL, &radial_values,
        BL_EXTEND_MODE_PAD, NULL, 0, NULL);
    bl_gradient_add_stop_rgba32(&radial, 0.0, 0xFFFFFFFFu);
    bl_gradient_add_stop_rgba32(&radial, 1.0, 0xFFFF6F3Fu);

    BLCircle circle = { 64, 64, 48 };
    bl_context_fill_geometry_ext(&ctx, BL_GEOMETRY_TYPE_CIRCLE, &circle, &radial);

    bl_gradient_destroy(&radial);

    /* Clean up */
    bl_context_destroy(&ctx);
    bl_image_destroy(&img);

    printf("blend2d 0.21.2 C API test: OK\n");
    return 0;
}
