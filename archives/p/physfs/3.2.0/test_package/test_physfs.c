#include <physfs.h>
#include <stdio.h>

int main(int argc, char **argv) {
    PHYSFS_Version version;
    const PHYSFS_ArchiveInfo **formats;

    if (!PHYSFS_init(argc > 0 ? argv[0] : "test_physfs"))
        return 1;
    PHYSFS_getLinkedVersion(&version);
    if (version.major != 3 || version.minor != 2 || version.patch != 0) {
        PHYSFS_deinit();
        return 2;
    }
    formats = PHYSFS_supportedArchiveTypes();
    if (!formats || !formats[0]) {
        PHYSFS_deinit();
        return 3;
    }
    printf("PhysicsFS %u.%u.%u supports %s archives\n",
           version.major, version.minor, version.patch, formats[0]->extension);
    return PHYSFS_deinit() ? 0 : 4;
}
