/*
 * Unit coverage for the production scaling predicate used by the OHOS X11
 * compatibility renderer.  A mismatched destination size must create a
 * cropped/scaled work image even when no color modifier or source crop is
 * requested; otherwise the renderer reads beyond the source image stride.
 */
#include <stdio.h>

#include "ohos_x11_scaling.h"

static int failures;

static void expect_decision(const char *name, int actual, int expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL: %s: expected %d, got %d\n",
                name, expected, actual);
        failures++;
    } else {
        printf("PASS: %s\n", name);
    }
}

int main(void)
{
    expect_decision(
        "identity dimensions do not scale",
        sxiv_needs_cropped_scaled_image(
            0, 0, 0, 10, 10, 10, 10, 10, 10),
        0);
    expect_decision(
        "color modifier forces a work image",
        sxiv_needs_cropped_scaled_image(
            1, 0, 0, 10, 10, 10, 10, 10, 10),
        1);
    expect_decision(
        "source offset forces a work image",
        sxiv_needs_cropped_scaled_image(
            0, 1, 0, 9, 10, 10, 10, 9, 10),
        1);
    expect_decision(
        "source crop forces a work image",
        sxiv_needs_cropped_scaled_image(
            0, 0, 0, 5, 5, 10, 10, 5, 5),
        1);
    expect_decision(
        "smaller destination forces a work image",
        sxiv_needs_cropped_scaled_image(
            0, 0, 0, 10, 10, 10, 10, 5, 10),
        1);
    expect_decision(
        "larger destination forces a work image",
        sxiv_needs_cropped_scaled_image(
            0, 0, 0, 10, 10, 10, 10, 20, 10),
        1);

    if (failures != 0) {
        fprintf(stderr, "test_sxiv_scaling: %d assertion(s) failed\n", failures);
        return 1;
    }
    puts("test_sxiv_scaling: 6 assertions passed");
    return 0;
}
