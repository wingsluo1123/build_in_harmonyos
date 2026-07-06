#include <stdio.h>
#include "blend2d.h"

int main(void) {
    uint32_t major, minor, patch;
    blGetVersion(&major, &minor, &patch);
    printf("blend2d version: %u.%u.%u\n", major, minor, patch);
    return 0;
}
