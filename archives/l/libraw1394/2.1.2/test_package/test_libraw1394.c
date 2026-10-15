#include <stdio.h>
#include <libraw1394/raw1394.h>
int main(void) {
    raw1394handle_t h = raw1394_new_handle();
    if (h) raw1394_destroy_handle(h);
    puts("libraw1394 consumer test passed");
    return 0;
}
