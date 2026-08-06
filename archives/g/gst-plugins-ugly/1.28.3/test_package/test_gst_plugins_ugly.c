#include <gst/gst.h>
#include <stdio.h>

/* gst-plugins-ugly plugin registration function (static build) */
extern void gst_plugin_asf_register(void);

int main(int argc, char **argv) {
    /* Initialize GStreamer */
    gst_init(&argc, &argv);

    /* Print version to verify gstreamer dependency chain */
    const char *version = gst_version_string();
    printf("GStreamer version: %s\n", version);

    /* Register the ASF plugin statically (verifies gst-plugins-ugly linked) */
    gst_plugin_register_static(
        GST_VERSION_MAJOR, GST_VERSION_MINOR,
        "asf",
        "ASF demuxer plugin",
        gst_plugin_asf_register,
        "1.28.3", "LGPL", "gst-plugins-ugly",
        "OpenHarmony", "https://gstreamer.freedesktop.org/");

    printf("gst-plugins-ugly: ASF plugin registered OK\n");

    return 0;
}
