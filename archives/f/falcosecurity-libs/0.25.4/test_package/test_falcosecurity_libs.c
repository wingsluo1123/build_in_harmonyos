#include <libscap/scap.h>

#include <stdio.h>

int main(void) {
    int failures = 0;

    // NOTE: PPM_API_CURRENT_VERSION and PPM syscall table macros are only
    // defined when the Linux driver subsystem is compiled. On OHOS these
    // are not available, so we test library API functions that exist in
    // the OHOS build (libscap non-Linux platform stubs). scap_get_host_root()
    // is a simple no-argument getter exported by the OHOS libscap build.

    const char *host_root = scap_get_host_root();
    if (host_root == NULL) {
        fprintf(stderr, "FAIL: host root is null\n");
        failures++;
    }

    if (failures == 0 && host_root[0] == '\0') {
        fprintf(stderr, "FAIL: host root is empty\n");
        failures++;
    }

    if (failures != 0) {
        return 1;
    }

    printf("falcosecurity-libs API test passed: host_root=%s\n", host_root);
    return 0;
}
