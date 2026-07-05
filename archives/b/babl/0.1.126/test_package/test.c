#include <stdio.h>
#include "babl/babl.h"

int main(void) {
    babl_init();
    printf("babl version: %s\n", babl_get_version());
    babl_exit();
    return 0;
}
