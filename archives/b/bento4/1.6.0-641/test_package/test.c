#include <stdio.h>
#include "Ap4Version.h"

int main(void) {
    unsigned int r[4];
    AP4_GetVersion(r);
    printf("bento4 version: %d.%d.%d.%d\n", r[0], r[1], r[2], r[3]);
    return 0;
}
