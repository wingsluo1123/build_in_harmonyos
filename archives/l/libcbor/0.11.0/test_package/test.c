#include <cbor.h>
#include <stdio.h>

int main(void) {
    cbor_item_t *item = cbor_new_definite_map(2);
    if (item == NULL) {
        fprintf(stderr, "cbor_new_definite_map failed\n");
        return 1;
    }
    printf("libcbor: cbor_new_definite_map OK\n");
    cbor_decref(&item);
    return 0;
}
