#include <gst/gst.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    gst_init(NULL, NULL);

    /* Test that gst-plugins-ugly asf plugin can be loaded */
    GstPlugin *plugin = gst_plugin_load_by_name("asf");
    if (plugin) {
        printf("gst-plugins-ugly: asf plugin loaded successfully\n");
        gst_object_unref(plugin);
    } else {
        printf("gst-plugins-ugly: asf plugin not found (may need GST_PLUGIN_PATH)\n");
    }

    printf("GStreamer version: %s\n", gst_version_string());
    return 0;
}
