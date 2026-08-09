#include <libgda/libgda.h>
#include <stdio.h>

int main(void) {
    /* Initialize libgda */
    gda_init();

    /* Check version */
    printf("libgda version: %s\n", LIBGDA_ABI_VERSION);

    /* Clean up */
    gda_cleanup();

    return 0;
}
