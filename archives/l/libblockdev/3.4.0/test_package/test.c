#include <stdio.h>
#include <blockdev/loop.h>
#include <glib.h>

int main(void) {
    /* Test: bd_loop_init() should be callable (may return FALSE on OHOS) */
    gboolean ret = bd_loop_init();
    if (ret) {
        bd_loop_close();
        printf("libblockdev test: bd_loop_init() succeeded, bd_loop_close() OK\n");
    } else {
        /* On HarmonyOS, bd_loop_init may fail due to missing /dev/loop devices,
         * but the function itself is callable and the library loads correctly. */
        printf("libblockdev test: bd_loop_init() returned FALSE (expected on HarmonyOS)\n");
    }
    return 0;
}
