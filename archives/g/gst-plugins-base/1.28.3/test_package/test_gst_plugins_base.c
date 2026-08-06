#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>
#include <stdio.h>

int main(void) {
    gst_init(NULL, NULL);
    gst_pb_utils_init();
    printf("gst-plugins-base initialized OK\n");
    return 0;
}
