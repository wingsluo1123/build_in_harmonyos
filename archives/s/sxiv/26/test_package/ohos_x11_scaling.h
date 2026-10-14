#ifndef SXIV_OHOS_X11_SCALING_H
#define SXIV_OHOS_X11_SCALING_H

/*
 * Test-package copy of the production predicate in the parent recipe.
 * Keep the predicate logic in sync with ../../ohos_x11_scaling.h.
 */
static inline int sxiv_needs_cropped_scaled_image(
    int has_color_modifier,
    int source_x, int source_y, int source_width, int source_height,
    int image_width, int image_height,
    int destination_width, int destination_height)
{
    return has_color_modifier != 0 ||
           source_x != 0 || source_y != 0 ||
           source_width != image_width || source_height != image_height ||
           destination_width != source_width ||
           destination_height != source_height;
}

#endif /* SXIV_OHOS_X11_SCALING_H */
