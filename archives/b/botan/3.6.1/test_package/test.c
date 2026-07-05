#include <stdio.h>
#include "botan/system.h"

int main(void) {
    printf("botan version: %s\n", botan_version_string());
    return 0;
}
