#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    printf("gstreamer version: %s\n", gst_version_string());
    return 0;
}
