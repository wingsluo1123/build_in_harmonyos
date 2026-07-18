#include <physfs.h>
#include <stdio.h>

int main(int argc, char **argv) {
    PHYSFS_Version compiled;
    PHYSFS_Version linked;
    const PHYSFS_ArchiveInfo **formats;
    const char *program = argc > 0 ? argv[0] : "test_physfs";

    if (!PHYSFS_init(program)) {
        fprintf(stderr, "PHYSFS_init(%s) failed: %s\n", program,
                PHYSFS_getErrorByCode(PHYSFS_getLastErrorCode()));
        return 1;
    }

    PHYSFS_VERSION(&compiled);
    PHYSFS_getLinkedVersion(&linked);
    if (compiled.major != linked.major || compiled.minor != linked.minor ||
        compiled.patch != linked.patch) {
        fprintf(stderr,
                "PhysicsFS header/library mismatch: compiled=%u.%u.%u "
                "linked=%u.%u.%u\n",
                compiled.major, compiled.minor, compiled.patch, linked.major,
                linked.minor, linked.patch);
        PHYSFS_deinit();
        return 2;
    }

    if (linked.major != 3 || linked.minor != 2 || linked.patch != 0) {
        fprintf(stderr, "Unexpected PhysicsFS upstream version: %u.%u.%u\n",
                linked.major, linked.minor, linked.patch);
        PHYSFS_deinit();
        return 3;
    }

    formats = PHYSFS_supportedArchiveTypes();
    if (!formats || !formats[0]) {
        fprintf(stderr, "PHYSFS_supportedArchiveTypes returned no formats\n");
        PHYSFS_deinit();
        return 4;
    }

    printf("PhysicsFS %u.%u.%u supports %s archives\n",
           linked.major, linked.minor, linked.patch, formats[0]->extension);

    if (!PHYSFS_deinit()) {
        fprintf(stderr, "PHYSFS_deinit failed: %s\n",
                PHYSFS_getErrorByCode(PHYSFS_getLastErrorCode()));
        return 5;
    }

    puts("PhysicsFS consumer test passed");
    return 0;
}
