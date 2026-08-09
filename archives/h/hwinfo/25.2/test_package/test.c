/* test_package/test.c — link against libhd and call hd_version() */
#include <stdio.h>
#include "hd.h"

int main(void) {
    /* Call libhd API to verify the library is correctly packaged */
    char *ver = hd_version();
    printf("hwinfo libhd version: %s\n", ver ? ver : "(null)");
    return 0;
}
