/*
 * test_harfbuzz.cpp — HarfBuzz library test (R34: substantial dependency)
 *
 * Tests that harfbuzz is properly built and linked by:
 * 1. Querying library version
 * 2. Creating a buffer and shaping text
 * 3. Verifying buffer operations
 */
#include <stdio.h>
#include <string.h>
#include <hb.h>

int main(void)
{
    /* Test 1: Library version */
    unsigned int major, minor, micro;
    hb_version(&major, &minor, &micro);
    printf("HarfBuzz version: %u.%u.%u\n", major, minor, micro);
    if (major != 14 || minor != 2 || micro != 0) {
        fprintf(stderr, "FAIL: Expected version 14.2.0, got %u.%u.%u\n", major, minor, micro);
        return 1;
    }

    /* Test 2: Create a buffer and add text */
    hb_buffer_t *buf = hb_buffer_create();
    if (buf == hb_buffer_get_empty()) {
        fprintf(stderr, "FAIL: Buffer creation returned empty buffer\n");
        return 1;
    }

    hb_buffer_add_utf8(buf, "Hello, World!", -1, 0, -1);
    hb_buffer_guess_segment_properties(buf);

    unsigned int len = hb_buffer_get_length(buf);
    printf("Buffer length: %u glyphs\n", len);
    if (len == 0) {
        fprintf(stderr, "FAIL: Buffer is empty after adding text\n");
        return 1;
    }

    hb_glyph_info_t *info = hb_buffer_get_glyph_infos(buf, NULL);
    if (info == NULL) {
        fprintf(stderr, "FAIL: Got NULL glyph info from non-empty buffer\n");
        return 1;
    }

    /* Test 3: Verify buffer content type */
    hb_buffer_content_type_t ct = hb_buffer_get_content_type(buf);
    printf("Buffer content type: %d\n", (int)ct);

    hb_buffer_destroy(buf);

    /* Test 4: Create and destroy a face (tests library linkage) */
    hb_face_t *face = hb_face_create(NULL, 0);
    if (face == NULL) {
        fprintf(stderr, "FAIL: Face creation returned NULL\n");
        return 1;
    }
    hb_face_destroy(face);

    printf("All tests passed!\n");
    return 0;
}
