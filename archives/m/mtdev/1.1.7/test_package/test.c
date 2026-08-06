#include <stdio.h>
#include <string.h>
#include <mtdev.h>

int main(void) {
    /* Verify struct mtdev is accessible from the library header */
    struct mtdev dev;
    memset(&dev, 0, sizeof(dev));

    /* Test mtdev_has_mt_event - checks if an MT event code is present.
     * With a zeroed-out struct, this should return 0 (no event). */
    int result = mtdev_has_mt_event(&dev, ABS_MT_POSITION_X);
    if (result != 0) {
        fprintf(stderr, "mtdev_has_mt_event returned unexpected value: %d\n", result);
        return 1;
    }

    /* Verify struct layout: state pointer should be NULL after memset */
    if (dev.state != NULL) {
        fprintf(stderr, "dev.state should be NULL after memset\n");
        return 1;
    }

    printf("test mtdev 1.1.7: OK\n");
    return 0;
}
