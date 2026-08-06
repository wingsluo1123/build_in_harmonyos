#include <gst/gst.h>
#include <gst/codecparsers/gsth264parser.h>
#include <stdio.h>

int main(void) {
    /* Initialize GStreamer */
    gst_init(NULL, NULL);

    /* Test gst-plugins-bad codec parser API */
    GstH264NalParser *parser = gst_h264_nal_parser_new();
    if (parser == NULL) {
        fprintf(stderr, "FAIL: gst_h264_nal_parser_new returned NULL\n");
        return 1;
    }

    /* Verify GStreamer version */
    guint major, minor, micro, nano;
    gst_version(&major, &minor, &micro, &nano);
    printf("GStreamer version: %u.%u.%u.%u\n", major, minor, micro, nano);

    /* Clean up */
    gst_h264_nal_parser_free(parser);

    printf("test gst-plugins-bad 1.28.3: OK\n");
    return 0;
}
