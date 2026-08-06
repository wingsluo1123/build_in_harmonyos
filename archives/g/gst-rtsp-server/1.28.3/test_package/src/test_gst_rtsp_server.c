#include <gst/gst.h>
#include <gst/rtsp-server/rtsp-server.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);

    guint major, minor, micro, nano;
    gst_version(&major, &minor, &micro, &nano);
    printf("GStreamer version: %u.%u.%u.%u\n", major, minor, micro, nano);

    /* Test gst-rtsp-server: create a server object */
    GstRTSPServer *server = gst_rtsp_server_new();
    if (server == NULL) {
        fprintf(stderr, "Failed to create RTSP server!\n");
        return 1;
    }
    printf("gst-rtsp-server: created GstRTSPServer successfully!\n");
    g_object_unref(server);

    return 0;
}
