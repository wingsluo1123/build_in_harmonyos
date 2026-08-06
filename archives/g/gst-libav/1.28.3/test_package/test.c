#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: Test must actually depend on the tested package.
 * gst-libav is a GStreamer plugin (.so), so we load it via dlopen
 * and verify the GStreamer plugin descriptor symbols exist. */

int main(void) {
    const char *plugin_dir;
    char path[4096];

    /* Get plugin directory from environment or use default */
    plugin_dir = getenv("GST_LIBAV_PLUGIN_PATH");
    if (!plugin_dir) {
        /* The conan package installs the plugin to lib/gstreamer-1.0/ */
        plugin_dir = "lib/gstreamer-1.0";
    }
    snprintf(path, sizeof(path), "%s/libgstlibav.so", plugin_dir);

    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "Failed to load %s: %s\n", path, dlerror());
        return 1;
    }
    printf("Loaded plugin: %s\n", path);

    /* Check for GStreamer plugin descriptor symbols */
    void *desc_sym = dlsym(handle, "gst_plugin_libav_get_desc");
    void *reg_sym = dlsym(handle, "gst_plugin_libav_register");
    if (desc_sym) {
        printf("Found gst_plugin_libav_get_desc symbol\n");
    } else {
        /* The symbol name might vary; check for alternative */
        void *desc2 = dlsym(handle, "gst_plugin_desc");
        if (desc2) {
            printf("Found gst_plugin_desc symbol\n");
        } else {
            fprintf(stderr, "No GStreamer plugin descriptor symbols found\n");
            dlclose(handle);
            return 1;
        }
    }
    if (reg_sym) {
        printf("Found gst_plugin_libav_register symbol\n");
    }

    /* Verify the plugin has reasonable size (not an empty stub) */
    FILE *f = fopen(path, "rb");
    if (f) {
        fseek(f, 0, SEEK_END);
        long size = ftell(f);
        fclose(f);
        printf("Plugin size: %ld bytes\n", size);
        if (size < 1000) {
            fprintf(stderr, "Plugin too small, likely a stub\n");
            dlclose(handle);
            return 1;
        }
    }

    dlclose(handle);
    printf("gst-libav plugin test: OK\n");
    return 0;
}
