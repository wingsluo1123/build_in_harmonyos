#ifndef SXIV_OHOS_X11_SCALING_H
#define SXIV_OHOS_X11_SCALING_H

/*
 * Decide whether the compatibility renderer must create a cropped/scaled
 * work image instead of reading pixels directly from the source image.
 * Keeping this predicate free of X11 and imlib2 types lets the installed
 * consumer test exercise every branch without an X display.
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
