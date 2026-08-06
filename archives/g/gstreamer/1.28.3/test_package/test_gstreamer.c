#include <gst/gst.h>
#include <stdio.h>

int main(void) {
    gst_init(NULL, NULL);
    printf("GStreamer version: %s\n", gst_version_string());
    return 0;
}
