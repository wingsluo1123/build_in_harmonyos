/*
 * svg2png - minimal SVG rasteriser for the toolbar icon generation step.
 *
 * Upstream converts the icon SVGs with Inkscape.  Inkscape is a big desktop
 * application that is not available on every build host, so this small
 * librsvg-based tool takes its place when CMake cannot find Inkscape.
 *
 * It accepts the same command line shape the CMake rules hand to Inkscape,
 *
 *     svg2png icon.svg -h 24 -o icon24.png
 *
 * and also answers --version / --help, which CMake/FindInkscape.cmake probes
 * for.  The icon is rendered so that its height is the requested number of
 * pixels; the width follows the SVG's own aspect ratio (the toolbar icons are
 * square, so width == height).
 */
#include <librsvg/rsvg.h>
#include <cairo.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	int i;
	const char *input = NULL;
	const char *output = NULL;
	double height = 0.0;

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--version") == 0) {
			/* FindInkscape.cmake parses a major.minor version out of this. */
			printf("svg2png (librsvg) 1.0\n");
			return 0;
		}
		if (strcmp(argv[i], "--help") == 0) {
			printf("usage: svg2png INPUT.svg -h HEIGHT -o OUTPUT.png\n");
			return 0;
		}
		if (strcmp(argv[i], "-h") == 0 && i + 1 < argc) {
			height = atof(argv[++i]);
		} else if (strncmp(argv[i], "-h", 2) == 0 && argv[i][2] != '\0') {
			height = atof(argv[i] + 2);
		} else if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
			output = argv[++i];
		} else if (strncmp(argv[i], "-o", 2) == 0 && argv[i][2] != '\0') {
			/* The CMake rules append the output name to ${Inkscape_EXPORT}
			 * without a separator, the same way they do for Inkscape's
			 * "--export-filename=" prefix, so accept "-oFILE" as well. */
			output = argv[i] + 2;
		} else if (argv[i][0] != '-' && input == NULL) {
			input = argv[i];
		}
	}
	if (input == NULL || output == NULL || height <= 0.0) {
		fprintf(stderr, "svg2png: usage: svg2png INPUT.svg -h HEIGHT -o OUTPUT.png\n");
		return 2;
	}

	GError *error = NULL;
	RsvgHandle *handle = rsvg_handle_new_from_file(input, &error);
	if (handle == NULL) {
		fprintf(stderr, "svg2png: cannot load %s: %s\n",
			input, error != NULL ? error->message : "unknown error");
		return 1;
	}

	/* Match Inkscape's -h: scale so the rendered image is "height" pixels tall. */
	double width = height;
	double intrinsic_width = 0.0, intrinsic_height = 0.0;
	if (rsvg_handle_get_intrinsic_size_in_pixels(handle, &intrinsic_width, &intrinsic_height)
	    && intrinsic_height > 0.0)
		width = height * intrinsic_width / intrinsic_height;

	int pixel_width = (int) (width + 0.5);
	int pixel_height = (int) (height + 0.5);
	if (pixel_width < 1)
		pixel_width = 1;
	if (pixel_height < 1)
		pixel_height = 1;

	cairo_surface_t *surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32,
							      pixel_width, pixel_height);
	cairo_t *cr = cairo_create(surface);
	RsvgRectangle viewport = { 0.0, 0.0, (double) pixel_width, (double) pixel_height };

	gboolean rendered = rsvg_handle_render_document(handle, cr, &viewport, &error);
	cairo_destroy(cr);
	if (!rendered) {
		fprintf(stderr, "svg2png: cannot render %s: %s\n",
			input, error != NULL ? error->message : "unknown error");
		cairo_surface_destroy(surface);
		g_object_unref(handle);
		return 1;
	}
	if (cairo_surface_write_to_png(surface, output) != CAIRO_STATUS_SUCCESS) {
		fprintf(stderr, "svg2png: cannot write %s\n", output);
		cairo_surface_destroy(surface);
		g_object_unref(handle);
		return 1;
	}
	cairo_surface_destroy(surface);
	g_object_unref(handle);
	return 0;
}
