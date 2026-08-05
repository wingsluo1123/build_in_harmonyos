#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <id3tag.h>

int main(void)
{
    int failures = 0;

    /* Test 1: Library version string */
    printf("libid3tag version: %s\n", id3_version);
    if (strlen(id3_version) == 0) {
        fprintf(stderr, "FAIL: id3_version is empty\n");
        failures++;
    }

    /* Test 2: Create a new ID3 tag */
    struct id3_tag *tag = id3_tag_new();
    if (!tag) {
        fprintf(stderr, "FAIL: id3_tag_new returned NULL\n");
        return 1;
    }
    printf("Created new ID3 tag (version 0x%04x)\n", id3_tag_version(tag));

    /* Test 3: Create and attach a title frame */
    struct id3_frame *frame = id3_frame_new(ID3_FRAME_TITLE);
    if (!frame) {
        fprintf(stderr, "FAIL: id3_frame_new returned NULL\n");
        id3_tag_delete(tag);
        return 1;
    }

    /* Set text encoding field (field 0) */
    union id3_field *field = id3_frame_field(frame, 0);
    if (field) {
        id3_field_settextencoding(field, ID3_FIELD_TEXTENCODING_ISO_8859_1);
    }

    /* Set title string (field 1) */
    field = id3_frame_field(frame, 1);
    if (field) {
        id3_latin1_t title[] = "Test Title";
        id3_ucs4_t *ucs4 = id3_latin1_ucs4duplicate(title);
        if (ucs4) {
            id3_field_setstrings(field, 1, &ucs4);
            free(ucs4);
        }
    }

    id3_tag_attachframe(tag, frame);
    printf("Attached TIT2 frame with title \"Test Title\"\n");

    /* Test 4: Render the tag to a byte buffer */
    id3_length_t query_size = id3_tag_render(tag, 0);
    if (query_size == 0) {
        fprintf(stderr, "FAIL: id3_tag_render (query) returned 0\n");
        failures++;
    } else {
        printf("Render query size: %lu bytes\n", (unsigned long)query_size);
    }

    id3_byte_t *buffer = (id3_byte_t *)malloc(query_size);
    if (!buffer) {
        fprintf(stderr, "FAIL: malloc failed\n");
        id3_tag_delete(tag);
        return 1;
    }

    id3_length_t actual_size = id3_tag_render(tag, buffer);
    printf("Rendered tag: %lu bytes\n", (unsigned long)actual_size);

    /* Test 5: Parse the rendered tag back */
    struct id3_tag *parsed = id3_tag_parse(buffer, actual_size);
    if (!parsed) {
        fprintf(stderr, "FAIL: id3_tag_parse returned NULL\n");
        free(buffer);
        id3_tag_delete(tag);
        return 1;
    }
    printf("Parsed tag version: 0x%04x\n", id3_tag_version(parsed));

    /* Test 6: Find the title frame in the parsed tag */
    struct id3_frame *parsed_frame = id3_tag_findframe(parsed, ID3_FRAME_TITLE, 0);
    if (!parsed_frame) {
        fprintf(stderr, "FAIL: id3_tag_findframe returned NULL for TIT2\n");
        failures++;
    } else {
        printf("Found TIT2 frame in parsed tag\n");
    }

    /* Cleanup */
    id3_tag_delete(parsed);
    free(buffer);
    id3_tag_delete(tag);

    /* Test 7: Genre database lookup */
    id3_ucs4_t const *genre = id3_genre_index(0);
    if (genre) {
        id3_latin1_t *genre_str = id3_ucs4_latin1duplicate(genre);
        if (genre_str) {
            printf("Genre[0]: %s\n", genre_str);
            free(genre_str);
        }
    } else {
        fprintf(stderr, "FAIL: id3_genre_index(0) returned NULL\n");
        failures++;
    }

    if (failures > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", failures);
        return 1;
    }

    printf("\nAll tests PASSED\n");
    return 0;
}
