#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    printf("GStreamer version: %s\n", gst_version_string());
    gst_deinit();
    return 0;
}
