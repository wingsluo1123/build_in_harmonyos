#include <stdio.h>
#include <stdlib.h>
#include <sord/sord.h>

int main(void) {
    /* Create a SordWorld and verify it is non-NULL. */
    SordWorld* world = sord_world_new();
    if (!world) {
        fprintf(stderr, "sord_world_new returned NULL\n");
        return 1;
    }
    printf("sord API test: OK\n");
    sord_world_free(world);
    return 0;
}
