#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sratom/sratom.h>
#include <lv2/urid/urid.h>
#include <sord/sord.h>
#include <serd/serd.h>

static uint32_t urid_map(LV2_URID_Map_Handle handle, const char* uri) {
    return (uint32_t)(uintptr_t)uri; /* naive: use address as ID */
}

int main(void) {
    SordWorld* world = sord_world_new();
    if (!world) {
        fprintf(stderr, "sord_world_new failed\n");
        return 1;
    }

    LV2_URID_Map map = { .handle = NULL, .map = urid_map };
    Sratom* sratom = sratom_new(&map);
    if (!sratom) {
        fprintf(stderr, "sratom_new failed\n");
        sord_world_free(world);
        return 1;
    }

    printf("sratom API test: OK\n");
    sratom_free(sratom);
    sord_world_free(world);
    return 0;
}
