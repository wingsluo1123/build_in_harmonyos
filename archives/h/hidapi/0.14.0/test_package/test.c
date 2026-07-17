#include <hidapi/hidapi.h>
#include <stdio.h>

int main(void) {
    int ret = hid_init();
    if (ret != 0) {
        fprintf(stderr, "hid_init failed: %d\n", ret);
        return 1;
    }
    printf("hidapi: hid_init OK\n");
    hid_exit();
    return 0;
}
