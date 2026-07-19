#include <stdio.h>
#include "discid/discid.h"

int main(void) {
    const char *ver = discid_get_version_string();
    if (ver == NULL) {
        fprintf(stderr, "ERROR: discid_get_version_string() returned NULL\n");
        return 1;
    }
    printf("libdiscid version: %s\n", ver);
    printf("libdiscid test OK\n");
    return 0;
}
