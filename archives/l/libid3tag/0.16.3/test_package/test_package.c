#include <stdio.h>
#include <id3tag.h>

int main(void) {
    printf("libid3tag version: %s\n", id3_version_string());
    struct id3_tag *tag = id3_tag_new(0x0400);
    if (!tag) { printf("FAIL: id3_tag_new\n"); return 1; }
    struct id3_frame *frame = id3_frame_new(ID3_FRAME_TITLE);
    if (!frame) { id3_tag_delete(tag); return 1; }
    id3_field_settextencoding(id3_field(frame, 0), ID3_FIELD_TEXTENCODING_UTF_8);
    union id3_field *field = id3_field(frame, 1);
    id3_field_setstrings(field, 1, (id3_ucs4_t*[]){ id3_ucs4_utf8duplicate((id3_utf8_t*)"Test Title") });
    id3_tag_attachframe(tag, frame);
    id3_length_t size = id3_tag_render(tag, 0);
    if (size == 0) { printf("FAIL: id3_tag_render returned 0\n"); id3_tag_delete(tag); return 1; }
    printf("Rendered tag: %lu bytes\n", (unsigned long)size);
    id3_tag_delete(tag);
    printf("All tests PASSED\n");
    return 0;
}
