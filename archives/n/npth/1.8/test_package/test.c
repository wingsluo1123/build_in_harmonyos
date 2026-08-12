#include <stdio.h>
#include <npth.h>

int main(void) {
    int rc = npth_init();
    if (rc != 0) {
        fprintf(stderr, "npth_init failed: %d\n", rc);
        return 1;
    }
    printf("npth 1.8: OK (npth_init succeeded)\n");
    return 0;
}
