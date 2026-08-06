#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    GstElement *sink = gst_element_factory_make("appsink", "test_sink");
    if (sink) {
        printf("appsink created successfully\n");
        gst_object_unref(sink);
    } else {
        printf("appsink creation failed\n");
    }
    printf("gstreamer version: %s\n", gst_version_string());
    return 0;
}
