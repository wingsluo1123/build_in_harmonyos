#include <stdio.h>
#include "kcapi.h"

int main(void) {
    unsigned int major, minor;
    kcapi_version(&major, &minor);
    printf("libkcapi version: %u.%u\n", major, minor);
    printf("libkcapi test OK\n");
    return 0;
}