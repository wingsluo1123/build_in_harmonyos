#include <libpsl.h>
#include <stdio.h>

int main(void) {
    /* Test: psl_free with NULL is a safe no-op */
    psl_free(NULL);
    printf("OK: libpsl 0.21.5 test passed\n");
    return 0;
}
