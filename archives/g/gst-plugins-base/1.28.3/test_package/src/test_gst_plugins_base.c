#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/pbutils/pbutils.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);

    guint major, minor, micro, nano;
    gst_version(&major, &minor, &micro, &nano);
    printf("GStreamer version: %u.%u.%u.%u\n", major, minor, micro, nano);

    /* Test gst-plugins-base pbutils initialization */
    gst_pb_utils_init();

    printf("gst-plugins-base initialization successful!\n");
    return 0;
}
