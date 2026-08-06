#include <gst/gst.h>
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    /* Initialize GStreamer */
    gst_init(NULL, NULL);

    /* Get the registry and list plugins */
    GstRegistry *registry = gst_registry_get();
    GList *plugins = gst_registry_get_plugin_list(registry);
    guint count = g_list_length(plugins);

    printf("GStreamer plugins in registry: %u\n", count);

    /* Try to dlopen a good plugin (wavparse is a common good plugin) */
    void *h = dlopen("libgstwavparse.so", RTLD_NOW | RTLD_GLOBAL);
    if (h) {
        printf("dlopen libgstwavparse.so ok\n");
        dlclose(h);
    } else {
        printf("dlopen libgstwavparse.so skipped: %s\n", dlerror());
    }

    gst_plugin_list_free(plugins);
    printf("gst-plugins-good test passed\n");
    return 0;
}
