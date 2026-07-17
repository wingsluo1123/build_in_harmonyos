#include <fido.h>
#include <stdio.h>

int main(void) {
    fido_init(0);
    printf("libfido2: fido_init OK\n");
    return 0;
}
