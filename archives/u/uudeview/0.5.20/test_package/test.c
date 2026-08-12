#include <stdio.h>
#include <uudeview.h>

int main(void) {
    /* Test that the uulib API is accessible */
    UUInitialize();
    UUCleanUp();
    printf("uudeview 0.5.20: uulib API test OK\n");
    return 0;
}
