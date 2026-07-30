#include <libscap/scap.h>

#include <stdio.h>

int main(void) {
    int failures = 0;

    // NOTE: PPM_API_CURRENT_VERSION and PPM syscall table macros are only
    // defined when the Linux driver subsystem is compiled. On OHOS these
    // are not available, so we test library API functions that exist in
    // the OHOS build (libscap non-Linux platform stubs).

    const struct scap_machine_info *info = scap_get_machine_info();
    if (info == NULL) {
        fprintf(stderr, "FAIL: machine info is null\n");
        failures++;
    }

    const char *agent = scap_get_agent_info();
    if (agent == NULL || agent[0] == '\0') {
        fprintf(stderr, "FAIL: agent info is unavailable\n");
        failures++;
    }

    if (failures != 0) {
        return 1;
    }

    printf("falcosecurity-libs API test passed: %s\n", agent);
    return 0;
}
