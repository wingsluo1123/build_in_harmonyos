#include <libhackrf/hackrf.h>

int main(void) {
    int result = hackrf_init();
    if (result == HACKRF_SUCCESS) {
        hackrf_exit();
        return 0;
    }
    return result == HACKRF_ERROR_LIBUSB ? 0 : 1;
}
