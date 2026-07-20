/* test_package/test.c — Conan L1 test for hwloc/2.12.2
 * R34: must substantively depend on the tested package's API.
 * Calls hwloc_topology_init/load/get_depth/destroy to verify the library
 * links and exports its core symbols correctly. */
#include <stdio.h>
#include <stdlib.h>
#include "hwloc.h"

int main(void) {
    hwloc_topology_t topology;
    int err;

    err = hwloc_topology_init(&topology);
    if (err) {
        fprintf(stderr, "hwloc_topology_init failed: %d\n", err);
        return EXIT_FAILURE;
    }

    err = hwloc_topology_load(topology);
    if (err) {
        fprintf(stderr, "hwloc_topology_load failed: %d\n", err);
        hwloc_topology_destroy(topology);
        return EXIT_FAILURE;
    }

    int depth = hwloc_topology_get_depth(topology);
    if (depth <= 0) {
        fprintf(stderr, "hwloc_topology_get_depth returned %d\n", depth);
        hwloc_topology_destroy(topology);
        return EXIT_FAILURE;
    }

    /* Sanity: root object exists and has a cpuset */
    hwloc_obj_t root = hwloc_get_root_obj(topology);
    if (!root || !root->cpuset || hwloc_bitmap_iszero(root->cpuset)) {
        fprintf(stderr, "root object has empty cpuset\n");
        hwloc_topology_destroy(topology);
        return EXIT_FAILURE;
    }

    printf("hwloc 2.12.2 OK: topology depth=%d\n", depth);
    hwloc_topology_destroy(topology);
    return EXIT_SUCCESS;
}
