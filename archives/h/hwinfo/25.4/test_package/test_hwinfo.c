#include <stdio.h>
#include <string.h>
#include "hd.h"

int main(void) {
    /* Call hd_version() from libhd to verify library is linked correctly */
    char *ver = hd_version();
    if (ver && strlen(ver) > 0) {
        printf("libhd version: %s\n", ver);
        return 0;
    }
    fprintf(stderr, "ERROR: hd_version() returned empty string\n");
    return 1;
}
