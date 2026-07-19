#include <stdio.h>
#include "rtl-sdr.h"

int main(void) {
    const char *ver = rtlsdr_get_version();
    if (ver == NULL) {
        fprintf(stderr, "ERROR: rtlsdr_get_version() returned NULL\n");
        return 1;
    }
    printf("librtlsdr version: %s\n", ver);
    printf("librtlsdr test OK\n");
    return 0;
}
