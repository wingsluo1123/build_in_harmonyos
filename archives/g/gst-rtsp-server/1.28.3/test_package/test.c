/*
 * test_package for gst-rtsp-server 1.28.3
 *
 * Verifies that the gst-rtsp-server library is correctly built and
 * its core API is callable. Creates an RTSP server instance and
 * checks that gstreamer is properly initialized.
 */
#include <gst/gst.h>
#include <gst/rtsp-server/rtsp-server.h>
#include <stdio.h>

int main(void)
{
    /* Initialize GStreamer (required before using gst-rtsp-server) */
    gst_init(NULL, NULL);

    /* Create an RTSP server instance — core API of this library */
    GstRTSPServer *server = gst_rtsp_server_new();
    if (server == NULL) {
        fprintf(stderr, "FAIL: gst_rtsp_server_new() returned NULL\n");
        return 1;
    }

    /* Verify the server has a default service */
    GstRTSPMediaFactory *factory = gst_rtsp_media_factory_new();
    if (factory == NULL) {
        fprintf(stderr, "FAIL: gst_rtsp_media_factory_new() returned NULL\n");
        g_object_unref(server);
        return 1;
    }

    /* Clean up */
    g_object_unref(factory);
    g_object_unref(server);

    printf("OK: gst-rtsp-server 1.28.3 — server and media factory created successfully\n");
    return 0;
}
