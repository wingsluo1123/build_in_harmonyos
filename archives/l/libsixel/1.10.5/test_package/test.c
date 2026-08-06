#include <stdio.h>
#include <sixel.h>

int main(void) {
    /* Test: create allocator — exercises the core libsixel API */
    sixel_allocator_t *allocator = NULL;
    SIXELSTATUS status = sixel_allocator_new(&allocator, NULL, NULL, NULL, NULL);
    if (SIXEL_FAILED(status)) {
        printf("libsixel test: FAILED (sixel_allocator_new returned 0x%04x)\n", status);
        return 1;
    }
    sixel_allocator_unref(allocator);
    printf("libsixel test: OK (version %s)\n", LIBSIXEL_VERSION);
    return 0;
}
