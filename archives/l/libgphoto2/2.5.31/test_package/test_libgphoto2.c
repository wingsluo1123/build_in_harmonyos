#include <stdio.h>
#include <gphoto2/gphoto2.h>

int main(void) {
    /* Initialize a Camera object to verify the library API works */
    Camera *camera;
    int ret = gp_camera_new(&camera);
    if (ret != GP_OK) {
        fprintf(stderr, "gp_camera_new failed: %d\n", ret);
        return 1;
    }
    gp_camera_free(camera);

    /* Verify library version info is accessible */
    GPContext *ctx = gp_context_new();
    if (!ctx) {
        fprintf(stderr, "gp_context_new returned NULL\n");
        return 1;
    }
    gp_context_unref(ctx);

    printf("libgphoto2 test PASSED: API calls successful\n");
    return 0;
}
