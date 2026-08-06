#include <gst/gst.h>
#include <gst/audio/audio.h>
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    /* Initialize GStreamer */
    gst_init(NULL, NULL);

    /* Verify base audio API is available */
    guint rate = 44100;
    guint64 samples = gst_util_uint64_scale(rate, GST_SECOND, 1);
    printf("Audio samples per second: %llu\n", (unsigned long long)samples);

    printf("GStreamer base API verified\n");
    return 0;
}
