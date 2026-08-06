#include <stdio.h>
#include <keyutils.h>

int main() {
    /* Test that we can call a keyutils function */
    key_serial_t key = KEY_SPEC_THREAD_KEYRING;
    printf("keyutils test: thread keyring spec = %d\n", key);
    return 0;
}
