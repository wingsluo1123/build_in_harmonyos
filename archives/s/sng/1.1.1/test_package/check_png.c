/* Consumer program for the sng test_package.
 *
 * Links libpng, decodes a PNG that was produced by the packaged `sng`
 * binary from sample.sng and verifies what sng wrote: geometry, palette
 * (X11 colour names resolved through the rgb.txt shipped by the package),
 * pixel indices and the tEXt chunk.  Exit status 0 only if all of it holds.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <png.h>

static int failures;

#define CHECK(cond, msg) \
	do { \
		if (!(cond)) { \
			fprintf(stderr, "FAIL: %s\n", msg); \
			failures++; \
		} \
	} while (0)

int main(int argc, char **argv)
{
	static const unsigned char want_pal[4][3] = {
		{255, 0, 0},    /* "red"             */
		{47, 79, 79},   /* "dark slate gray" */
		{255, 215, 0},  /* "gold"            */
		{0, 0, 255},    /* literal           */
	};
	static const unsigned char want_rows[2][4] = {{0, 1, 2, 3}, {3, 2, 1, 0}};
	png_structp png;
	png_infop info;
	png_colorp pal = NULL;
	png_textp text = NULL;
	png_bytep rows[2];
	unsigned char buf[2][4];
	png_uint_32 w, h;
	int depth, ctype, npal = 0, ntext = 0, i, j, found_title = 0;
	FILE *fp;

	if (argc != 2) {
		fprintf(stderr, "usage: %s file.png\n", argv[0]);
		return 2;
	}
	fp = fopen(argv[1], "rb");
	if (!fp) {
		perror(argv[1]);
		return 2;
	}
	png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	info = png ? png_create_info_struct(png) : NULL;
	if (!png || !info || setjmp(png_jmpbuf(png))) {
		fprintf(stderr, "FAIL: %s is not a readable PNG\n", argv[1]);
		return 1;
	}
	png_init_io(png, fp);
	png_read_info(png, info);
	png_get_IHDR(png, info, &w, &h, &depth, &ctype, NULL, NULL, NULL);
	CHECK(w == 4 && h == 2, "geometry is 4x2");
	CHECK(depth == 8, "bit depth is 8");
	CHECK(ctype == PNG_COLOR_TYPE_PALETTE, "colour type is palette");

	png_get_PLTE(png, info, &pal, &npal);
	CHECK(npal == 4, "palette has 4 entries");
	for (i = 0; i < npal && i < 4; i++) {
		CHECK(pal[i].red == want_pal[i][0] && pal[i].green == want_pal[i][1] &&
		      pal[i].blue == want_pal[i][2], "palette entry matches X11 rgb.txt value");
		if (pal[i].red != want_pal[i][0] || pal[i].green != want_pal[i][1] ||
		    pal[i].blue != want_pal[i][2])
			fprintf(stderr, "  entry %d: got (%d,%d,%d)\n", i,
			        pal[i].red, pal[i].green, pal[i].blue);
	}

	rows[0] = buf[0];
	rows[1] = buf[1];
	memset(buf, 0xff, sizeof(buf));
	png_read_image(png, rows);
	png_read_end(png, info);
	for (i = 0; i < 2; i++)
		for (j = 0; j < 4; j++)
			CHECK(buf[i][j] == want_rows[i][j], "pixel index matches sample.sng");

	if (png_get_text(png, info, &text, &ntext) > 0)
		for (i = 0; i < ntext; i++)
			if (!strcmp(text[i].key, "Title") && !strcmp(text[i].text, "ohos-consumer"))
				found_title = 1;
	CHECK(found_title, "tEXt Title=ohos-consumer present");

	png_destroy_read_struct(&png, &info, NULL);
	fclose(fp);
	if (failures)
		return 1;
	printf("check_png: OK (4x2 palette, rgb.txt names resolved, pixels + tEXt match)\n");
	return 0;
}
