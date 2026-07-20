#include <libscap/scap.h>
#include <libscap/scap_api_version.h>

#include <stdio.h>

int main(void) {
    int failures = 0;

    if (!scap_is_api_compatible(PPM_API_CURRENT_VERSION, SCAP_MINIMUM_DRIVER_API_VERSION)) {
        fprintf(stderr, "FAIL: current driver API is not compatible\n");
        failures++;
    }

    const struct ppm_event_info *events = scap_get_event_info_table();
    if (events == NULL) {
        fprintf(stderr, "FAIL: event information table is null\n");
        failures++;
    }

    const char *read_name = scap_get_ppm_sc_name(PPM_SC_READ);
    if (read_name == NULL || read_name[0] == '\0') {
        fprintf(stderr, "FAIL: read syscall name is unavailable\n");
        failures++;
    }

    if (failures != 0) {
        return 1;
    }

    printf("falcosecurity-libs API test passed: %s\n", read_name);
    return 0;
}
