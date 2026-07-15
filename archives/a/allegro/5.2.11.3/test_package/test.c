#include <allegro5/allegro.h>
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint32_t version = al_get_allegro_version();
    int major = (version >> 24) & 0xff;
    int minor = (version >> 16) & 0xff;
    int revision = (version >> 8) & 0xff;
    int fix = version & 0xff;
    printf("allegro version: %d.%d.%d.%d\n", major, minor, revision, fix);
    if (major != 5 || minor != 2) {
        printf("FAIL: expected version 5.2.x\n");
        return 1;
    }
    printf("test allegro 5.2.11.3: OK\n");
    return 0;
}
