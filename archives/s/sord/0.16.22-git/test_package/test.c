#include <stdio.h>
#include <stdlib.h>
#include <sord/sord.h>

int main(void) {
    SordWorld* world = sord_world_new();
    if (!world) {
        fprintf(stderr, "sord_world_new failed\n");
        return 1;
    }
    printf("sord API test: OK\n");
    sord_world_free(world);
    return 0;
}
