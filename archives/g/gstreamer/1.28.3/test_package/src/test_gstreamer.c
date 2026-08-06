#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);

    guint major, minor, micro, nano;
    gst_version(&major, &minor, &micro, &nano);
    printf("GStreamer version: %u.%u.%u.%u\n", major, minor, micro, nano);

    if (major != 1 || minor != 28) {
        fprintf(stderr, "Unexpected GStreamer version!\n");
        return 1;
    }

    printf("GStreamer initialization successful!\n");
    return 0;
}
