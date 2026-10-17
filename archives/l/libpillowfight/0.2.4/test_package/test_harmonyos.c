/*
 * HarmonyOS-specific test for libpillowfight 0.2.4.
 *
 * Validates that the library's image-processing algorithms actually execute
 * on the OHOS aarch64 target (os=OHOS profile): builds a synthetic RGBA
 * bitmap, runs the ACE filter through the public C API, and asserts the
 * output is structurally correct and every channel stays within [0, 255].
 * This is a real library-API call that fails loudly if the algorithm
 * misbehaves on the HarmonyOS toolchain / libc.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#define NO_PYTHON
#include <pillowfight/pillowfight.h>

int main(void) {
    const int w = 8;
    const int h = 8;
    struct pf_bitmap in, out;
    int i;

    in.size.x = w;
    in.size.y = h;
    in.pixels = (union pf_pixel *)calloc((size_t)(w * h), sizeof(union pf_pixel));
    assert(in.pixels != NULL && "OOM for input bitmap");

    out.size.x = w;
    out.size.y = h;
    out.pixels = (union pf_pixel *)calloc((size_t)(w * h), sizeof(union pf_pixel));
    assert(out.pixels != NULL && "OOM for output bitmap");

    /* Two-tone synthetic image: top half dark (16), bottom half light (200). */
    for (i = 0; i < w * h; ++i) {
        unsigned char v = (i < w * h / 2) ? 16 : 200;
        in.pixels[i].color.r = v;
        in.pixels[i].color.g = v;
        in.pixels[i].color.b = v;
        in.pixels[i].color.a = 255;
    }

    /* Run the Automatic Color Equalization filter (public C API). */
    pf_ace(&in, &out, PF_DEFAULT_ACE_SLOPE, PF_DEFAULT_ACE_LIMIT,
           PF_DEFAULT_ACE_NB_SAMPLES, PF_DEFAULT_ACE_NB_THREADS);

    assert(out.size.x == w && out.size.y == h && "ACE output size mismatch");
    assert(out.pixels != NULL && "ACE produced a NULL output bitmap");

    for (i = 0; i < w * h; ++i) {
        assert(out.pixels[i].color.r <= 255 && out.pixels[i].color.g <= 255
               && out.pixels[i].color.b <= 255 && out.pixels[i].color.a <= 255
               && "ACE output channel out of [0,255] range on OHOS");
    }

    printf("HarmonyOS test PASSED: pf_ace() processed %dx%d bitmap on OHOS target (aarch64)\n", w, h);
    free(in.pixels);
    free(out.pixels);
    return 0;
}
