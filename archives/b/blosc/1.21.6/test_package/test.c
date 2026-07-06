#include <stdio.h>
#include "blosc.h"

int main(void) {
    int major, minor, patch;
    blosc_get_version_numbers(&major, &minor, &patch);
    printf("blosc version: %d.%d.%d\n", major, minor, patch);
    return 0;
}
