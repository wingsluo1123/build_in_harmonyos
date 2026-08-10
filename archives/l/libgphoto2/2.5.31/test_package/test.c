#include <stdio.h>
#include <stdlib.h>

/* Real libgphoto2 API test (R34): call actual library functions */
#include <gphoto2/gphoto2.h>
#include <gphoto2/gphoto2-version.h>
#include <gphoto2/gphoto2-context.h>

int main(void) {
    int ret;
    GPContext *ctx = NULL;
    Camera *cam = NULL;

    /* Get library version string */
    const char **ver = gp_library_version(GP_VERSION_SHORT);
    if (ver && ver[0]) {
        printf("libgphoto2 version: %s\n", ver[0]);
    } else {
        fprintf(stderr, "FAIL: gp_library_version returned NULL\n");
        return 1;
    }

    /* Create a context */
    ctx = gp_context_new();
    if (!ctx) {
        fprintf(stderr, "FAIL: gp_context_new returned NULL\n");
        return 1;
    }
    printf("gp_context_new: OK\n");

    /* Create a camera object */
    ret = gp_camera_new(&cam);
    if (ret < GP_OK) {
        fprintf(stderr, "FAIL: gp_camera_new returned %d\n", ret);
        gp_context_unref(ctx);
        return 1;
    }
    printf("gp_camera_new: OK\n");

    /* Cleanup */
    gp_camera_free(cam);
    gp_context_unref(ctx);

    printf("test libgphoto2 2.5.31: ALL TESTS PASSED\n");
    return 0;
}
