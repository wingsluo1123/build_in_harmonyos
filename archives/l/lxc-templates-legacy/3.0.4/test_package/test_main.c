#include <unistd.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <package_folder>\n", argv[0]);
        return 1;
    }
    char path[512];
    /* Verify lxc-alpine template is installed by the package */
    snprintf(path, sizeof(path), "%s/share/lxc/templates/lxc-alpine", argv[1]);
    if (access(path, F_OK) != 0) {
        fprintf(stderr, "FAIL: template not found: %s\n", path);
        return 1;
    }
    /* Verify lxc-debian template is installed */
    snprintf(path, sizeof(path), "%s/share/lxc/templates/lxc-debian", argv[1]);
    if (access(path, F_OK) != 0) {
        fprintf(stderr, "FAIL: template not found: %s\n", path);
        return 1;
    }
    /* Verify config file is installed */
    snprintf(path, sizeof(path), "%s/share/lxc/config/alpine.common.conf", argv[1]);
    if (access(path, F_OK) != 0) {
        fprintf(stderr, "FAIL: config not found: %s\n", path);
        return 1;
    }
    printf("OK: lxc-templates-legacy templates and configs verified\n");
    return 0;
}
