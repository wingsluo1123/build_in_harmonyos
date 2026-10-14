/*
 * Compatibility implementation for the X11 rendering API that is omitted
 * from the published imlib2/1.9.1 package.
 *
 * The OHPCD imlib2 recipe is built with --without-x, so its public header
 * and library do not expose imlib2's display and drawable functions.  sxiv
 * only needs those functions to put already-rasterised imlib2 images onto
 * an X11 drawable.  This file keeps the imlib2 image pipeline intact and
 * provides the missing drawable operations using libX11.  There are no
 * dummy return values: image loading, scaling, colour modifiers and alpha
 * blending all run through the published imlib2 package.
 */
#include <stdint.h>

#include "ohos_x11_scaling.h"

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <Imlib2.h>

static Display *sxiv_display;
static Visual *sxiv_visual;
static Colormap sxiv_colormap;
static Drawable sxiv_drawable;
static Pixmap sxiv_mask;

void imlib_context_set_display(Display *display)
{
    sxiv_display = display;
}

Display *imlib_context_get_display(void)
{
    return sxiv_display;
}

void imlib_context_disconnect_display(void)
{
    sxiv_display = NULL;
}

void imlib_context_set_visual(Visual *visual)
{
    sxiv_visual = visual;
}

Visual *imlib_context_get_visual(void)
{
    return sxiv_visual;
}

void imlib_context_set_colormap(Colormap colormap)
{
    sxiv_colormap = colormap;
}

Colormap imlib_context_get_colormap(void)
{
    return sxiv_colormap;
}

void imlib_context_set_drawable(Drawable drawable)
{
    sxiv_drawable = drawable;
}

Drawable imlib_context_get_drawable(void)
{
    return sxiv_drawable;
}

void imlib_context_set_mask(Pixmap mask)
{
    sxiv_mask = mask;
}

Pixmap imlib_context_get_mask(void)
{
    return sxiv_mask;
}

static int mask_shift(unsigned long mask)
{
    int shift = 0;

    while (mask != 0UL && (mask & 1UL) == 0UL) {
        mask >>= 1;
        shift++;
    }
    return shift;
}

static unsigned long mask_max(unsigned long mask)
{
    int shift = mask_shift(mask);

    return mask >> shift;
}

static unsigned char unpack_channel(unsigned long pixel, unsigned long mask)
{
    unsigned long maximum;
    unsigned long value;

    if (mask == 0UL) {
        return 0;
    }
    maximum = mask_max(mask);
    value = (pixel >> mask_shift(mask)) & maximum;
    return (unsigned char)((value * 255UL + maximum / 2UL) / maximum);
}

static unsigned long pack_channel(unsigned char value, unsigned long mask)
{
    unsigned long maximum;
    unsigned long scaled;

    if (mask == 0UL) {
        return 0UL;
    }
    maximum = mask_max(mask);
    scaled = ((unsigned long)value * maximum + 127UL) / 255UL;
    return (scaled << mask_shift(mask)) & mask;
}

static unsigned long pack_pixel(uint32_t pixel, Visual *visual)
{
    unsigned char red = (unsigned char)((pixel >> 16) & 0xffU);
    unsigned char green = (unsigned char)((pixel >> 8) & 0xffU);
    unsigned char blue = (unsigned char)(pixel & 0xffU);

    if (visual->red_mask == 0UL && visual->green_mask == 0UL &&
        visual->blue_mask == 0UL) {
        return (unsigned long)(pixel & 0x00ffffffU);
    }
    return pack_channel(red, visual->red_mask) |
           pack_channel(green, visual->green_mask) |
           pack_channel(blue, visual->blue_mask);
}

static unsigned long blend_pixel(uint32_t pixel, unsigned long destination,
                                 Visual *visual)
{
    unsigned char alpha = (unsigned char)((pixel >> 24) & 0xffU);
    unsigned char red = (unsigned char)((pixel >> 16) & 0xffU);
    unsigned char green = (unsigned char)((pixel >> 8) & 0xffU);
    unsigned char blue = (unsigned char)(pixel & 0xffU);
    unsigned char dest_red;
    unsigned char dest_green;
    unsigned char dest_blue;

    if (alpha == 0U) {
        return destination;
    }
    if (alpha == 255U) {
        return pack_pixel(pixel, visual);
    }
    dest_red = unpack_channel(destination, visual->red_mask);
    dest_green = unpack_channel(destination, visual->green_mask);
    dest_blue = unpack_channel(destination, visual->blue_mask);
    red = (unsigned char)(((unsigned int)red * alpha +
                           (unsigned int)dest_red * (255U - alpha) + 127U) / 255U);
    green = (unsigned char)(((unsigned int)green * alpha +
                             (unsigned int)dest_green * (255U - alpha) + 127U) / 255U);
    blue = (unsigned char)(((unsigned int)blue * alpha +
                            (unsigned int)dest_blue * (255U - alpha) + 127U) / 255U);
    return pack_channel(red, visual->red_mask) |
           pack_channel(green, visual->green_mask) |
           pack_channel(blue, visual->blue_mask);
}

static void draw_region(int source_x, int source_y, int source_width,
                        int source_height, int destination_x,
                        int destination_y, int destination_width,
                        int destination_height)
{
    Imlib_Image source;
    Imlib_Image work = NULL;
    Imlib_Color_Modifier modifier;
    Visual *visual;
    XImage *output;
    XImage *destination = NULL;
    const uint32_t *pixels;
    GC gc;
    int image_width;
    int image_height;
    int x;
    int y;
    int has_alpha;

    if (sxiv_display == NULL || sxiv_drawable == None) {
        return;
    }
    source = imlib_context_get_image();
    if (source == NULL) {
        return;
    }
    image_width = imlib_image_get_width();
    image_height = imlib_image_get_height();
    if (image_width <= 0 || image_height <= 0 ||
        source_width <= 0 || source_height <= 0 ||
        destination_width <= 0 || destination_height <= 0 ||
        source_x < 0 || source_y < 0 ||
        source_x + source_width > image_width ||
        source_y + source_height > image_height) {
        return;
    }
    modifier = imlib_context_get_color_modifier();
    if (sxiv_needs_cropped_scaled_image(
            modifier != NULL, source_x, source_y, source_width, source_height,
            image_width, image_height, destination_width, destination_height)) {
        work = imlib_create_cropped_scaled_image(
            source_x, source_y, source_width, source_height,
            destination_width, destination_height);
        if (work == NULL) {
            return;
        }
        imlib_context_set_image(work);
        if (modifier != NULL) {
            imlib_apply_color_modifier();
        }
    } else {
        imlib_context_set_image(source);
    }
    image_width = imlib_image_get_width();
    image_height = imlib_image_get_height();
    pixels = imlib_image_get_data_for_reading_only();
    if (pixels == NULL) {
        if (work != NULL) {
            imlib_free_image();
            imlib_context_set_image(source);
        }
        return;
    }
    has_alpha = imlib_image_has_alpha();
    visual = sxiv_visual != NULL
        ? sxiv_visual
        : DefaultVisual(sxiv_display, DefaultScreen(sxiv_display));
    output = XCreateImage(sxiv_display, visual,
                          DefaultDepth(sxiv_display, DefaultScreen(sxiv_display)),
                          ZPixmap, 0, NULL, (unsigned int)destination_width,
                          (unsigned int)destination_height, 32, 0);
    if (output == NULL) {
        if (work != NULL) {
            imlib_free_image();
            imlib_context_set_image(source);
        }
        return;
    }
    if (has_alpha) {
        destination = XGetImage(sxiv_display, sxiv_drawable,
                                destination_x, destination_y,
                                (unsigned int)destination_width,
                                (unsigned int)destination_height,
                                AllPlanes, ZPixmap);
    }
    for (y = 0; y < destination_height; y++) {
        for (x = 0; x < destination_width; x++) {
            uint32_t pixel = pixels[(size_t)y * (size_t)image_width + (size_t)x];
            unsigned long output_pixel;

            if (destination != NULL) {
                output_pixel = blend_pixel(
                    pixel, XGetPixel(destination, x, y), visual);
            } else {
                output_pixel = pack_pixel(pixel, visual);
            }
            XPutPixel(output, x, y, output_pixel);
        }
    }
    gc = XCreateGC(sxiv_display, sxiv_drawable, 0, NULL);
    if (gc != NULL) {
        XPutImage(sxiv_display, sxiv_drawable, gc, output, 0, 0,
                  destination_x, destination_y,
                  (unsigned int)destination_width,
                  (unsigned int)destination_height);
        XFreeGC(sxiv_display, gc);
    }
    if (destination != NULL) {
        XDestroyImage(destination);
    }
    XDestroyImage(output);
    if (work != NULL) {
        imlib_free_image();
        imlib_context_set_image(source);
    }
}

void imlib_render_image_on_drawable(int x, int y)
{
    Imlib_Image image = imlib_context_get_image();
    int width;
    int height;

    if (image == NULL) {
        return;
    }
    width = imlib_image_get_width();
    height = imlib_image_get_height();
    draw_region(0, 0, width, height, x, y, width, height);
}

void imlib_render_image_on_drawable_at_size(int x, int y, int width, int height)
{
    Imlib_Image image = imlib_context_get_image();
    int source_width;
    int source_height;

    if (image == NULL) {
        return;
    }
    source_width = imlib_image_get_width();
    source_height = imlib_image_get_height();
    draw_region(0, 0, source_width, source_height, x, y, width, height);
}

void imlib_render_image_part_on_drawable_at_size(
    int source_x, int source_y, int source_width, int source_height,
    int x, int y, int width, int height)
{
    draw_region(source_x, source_y, source_width, source_height,
                x, y, width, height);
}
