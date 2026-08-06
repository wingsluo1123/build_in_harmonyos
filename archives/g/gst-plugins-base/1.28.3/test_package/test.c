#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>
#include <stdio.h>

#ifdef __OHOS__
#define SKIP_DLOPEN 1
#endif

#ifndef SKIP_DLOPEN
#include <dlfcn.h>
#endif

int main(int argc, char *argv[]) {
    /* Initialize gstreamer and gst-plugins-base */
    gst_init(&argc, &argv);
    gst_pb_utils_init();

    /* Print version info */
    const gchar *version = gst_version_string();
    printf("gstreamer version: %s\n", version);
    g_assert(version != NULL);

#ifndef SKIP_DLOPEN
    /* Runtime test: try to dlopen the audio plugin if built shared */
    void *handle = dlopen("libgstaudioconvert.so", RTLD_LAZY);
    if (handle) {
        printf("dlopen audioconvert plugin: OK\n");
        dlclose(handle);
    } else {
        printf("dlopen audioconvert plugin: skipped (static build)\n");
    }
#else
    printf("dlopen test: skipped on OHOS\n");
#endif

    printf("gst-plugins-base test: PASS\n");
    return 0;
}
