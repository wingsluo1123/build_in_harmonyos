#include <stdio.h>
#include "discid/discid.h"

int main(void) {
    const char *ver = discid_get_version_string();
    printf("libdiscid version: %s\n", ver);
    printf("libdiscid test OK\n");
    return 0;
}