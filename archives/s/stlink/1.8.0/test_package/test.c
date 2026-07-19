#include <stddef.h>
#include <stlink.h>

int main(void) {
    stlink_t *device = stlink_open_usb(0, 0, NULL, 0);
    if (device != NULL) {
        stlink_close(device);
    }
    return 0;
}
