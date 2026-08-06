#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    /* Initialize GStreamer — verifies the library links and loads */
    gst_init(&argc, &argv);

    /* Print GStreamer version to verify the API is accessible */
    printf("GStreamer version: %s\n", gst_version_string());

    printf("gstreamer test: PASS\n");
    return 0;
}
