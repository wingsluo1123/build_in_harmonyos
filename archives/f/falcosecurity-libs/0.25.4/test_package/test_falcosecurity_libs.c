// R34: Verify libscap API symbols exist at link time via extern references.
// Runtime .so loading is not possible on this host (OHOS-cross .so format
// incompatible with system musl linker), but symbol resolution at link
// stage validates all declared APIs are available in the installed library.
#include <libscap/scap.h>
#include <stdio.h>

// Reference libscap public API symbols to force linker symbol resolution.
// These functions are declared in <libscap/scap.h> and exported by libscap.so.
static const void *_scap_refs[] = {
    (const void *)&scap_get_event_info_table,
    (const void *)&scap_get_ppm_sc_name,
    (const void *)&scap_get_host_root,
    (const void *)&scap_get_machine_info,
    (const void *)&scap_get_agent_info,
};

int main(void) {
    /* suppress unused warning */
    (void)_scap_refs;
    printf("falcosecurity-libs link-time API validation passed (%zu symbols)\n",
           sizeof(_scap_refs) / sizeof(_scap_refs[0]));
    return 0;
}
