/* gst-plugins-base 1.28.3 — consumer API verification.
 *
 * Calls gst_init() (from gstreamer dependency) and gst_pb_utils_init()
 * (from gst-plugins-base's libgstpbutils-1.0) to prove the Conan
 * package is wired correctly and the library chain links and runs.
 */
#include <gst/gst.h>
#include <gst/pbutils/pbutils.h>
#include <stdio.h>

int main(void) {
    /* Initialize GStreamer core (from gstreamer/1.28.3 dependency) */
    gst_init(NULL, NULL);

    /* Initialize gst-plugins-base pbutils library (from tested package) */
    gst_pb_utils_init();

    /* Print version info to verify the library is loaded */
    guint major, minor, micro, nano;
    gst_version(&major, &minor, &micro, &nano);
    printf("GStreamer version: %u.%u.%u.%u\n", major, minor, micro, nano);

    printf("gst-plugins-base test: PASS\n");
    return 0;
}
