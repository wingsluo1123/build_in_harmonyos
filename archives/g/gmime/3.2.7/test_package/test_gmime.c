#include <gmime/gmime.h>
#include <stdio.h>

int main(void) {
    printf("gmime version: %d.%d.%d\n",
           gmime_major_version, gmime_minor_version, gmime_micro_version);
    if (gmime_major_version == GMIME_MAJOR_VERSION) {
        printf("OK: header and library versions match\n");
        return 0;
    }
    fprintf(stderr, "ERROR: version mismatch\n");
    return 1;
}
