#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    const gchar *version = gst_version_string();
    if (version == NULL) {
        return 1;
    }
    g_print("GStreamer version: %s\n", version);

    /* Verify gst-plugins-bad is linked by checking for its libraries */
    GstPlugin *plugin = gst_plugin_load_by_name("accurip");
    if (plugin != NULL) {
        g_print("gst-plugins-bad plugin 'accurip' loaded successfully\n");
        gst_object_unref(plugin);
    } else {
        g_print("ERROR: 'accurip' plugin not found - gst-plugins-bad may not be properly installed\n");
        return 1;
    }

    gst_deinit();
    return 0;
}
