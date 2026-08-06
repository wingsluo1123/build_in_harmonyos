#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    gst_pb_utils_init();
    printf("GStreamer base utils initialized\n");
    printf("GStreamer version: %s\n", gst_version_string());
    return 0;
}
