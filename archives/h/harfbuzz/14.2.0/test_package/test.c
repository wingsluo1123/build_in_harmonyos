#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <hb.h>
#include <hb-ft.h>

int main(void) {
    printf("HarfBuzz version: %s\n", hb_version_string());

    // Test core API: buffer creation, shaping
    hb_buffer_t *buf = hb_buffer_create();
    if (!buf) {
        printf("FAIL: hb_buffer_create() returned NULL\n");
        return 1;
    }

    hb_buffer_add_utf8(buf, "Hello", -1, 0, -1);
    hb_buffer_guess_segment_properties(buf);

    hb_blob_t *blob = hb_blob_create_from_file_or_fail(NULL);
    hb_face_t *face = hb_face_create(blob, 0);
    hb_font_t *font = hb_font_create(face);

    hb_shape(font, buf, NULL, 0);

    unsigned int glyph_count;
    hb_glyph_info_t *glyphs = hb_buffer_get_glyph_infos(buf, &glyph_count);
    printf("Shaped %u glyphs\n", glyph_count);

    hb_font_destroy(font);
    hb_face_destroy(face);
    hb_blob_destroy(blob);
    hb_buffer_destroy(buf);

    printf("HarfBuzz core API test: PASS\n");
    return 0;
}
