#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);

    /* Check that gst-plugins-good plugins are available */
    GstRegistry *registry = gst_registry_get();
    GList *plugins = gst_registry_get_plugin_list(registry);

    int good_plugin_count = 0;
    for (GList *l = plugins; l != NULL; l = l->next) {
        GstPlugin *plugin = GST_PLUGIN(l->data);
        const gchar *name = gst_plugin_get_name(plugin);
        /* Check for some well-known gst-plugins-good plugins */
        if (g_str_has_prefix(name, "audioparsers") ||
            g_str_has_prefix(name, "isomp4") ||
            g_str_has_prefix(name, "matroska") ||
            g_str_has_prefix(name, "rtp") ||
            g_str_has_prefix(name, "wavparse")) {
            good_plugin_count++;
        }
    }
    gst_plugin_list_free(plugins);

    if (good_plugin_count > 0) {
        printf("Found %d gst-plugins-good plugins\n", good_plugin_count);
        return 0;
    } else {
        printf("No gst-plugins-good plugins found\n");
        return 1;
    }
}
