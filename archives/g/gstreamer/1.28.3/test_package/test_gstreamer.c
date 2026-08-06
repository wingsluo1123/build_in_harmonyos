#include <gst/gst.h>
#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libgstreamer-1.0.so"
#endif

int main(int argc, char **argv) {
    /* Initialize GStreamer */
    gst_init(&argc, &argv);

    /* Print version info */
    printf("GStreamer version: %s\n", gst_version_string());

    /* dlopen the core library to verify runtime loading */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("dlopen %s ok\n", TARGET_SO);
    dlclose(h);

    return 0;
}
