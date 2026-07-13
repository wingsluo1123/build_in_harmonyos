#include <stdio.h>
#include <string.h>
#include <libuecc/ecc.h>

int main(void) {
    ecc_int256_t zero;
    memset(&zero, 0, sizeof(zero));

    /* Test: zero is a zero element in GF(2^255-19) */
    int is_zero = ecc_25519_gf_is_zero(&zero);
    if (is_zero) {
        printf("test libuecc 7: OK (gf_is_zero passed)\n");
        return 0;
    } else {
        printf("test libuecc 7: FAIL (gf_is_zero expected true)\n");
        return 1;
    }
}
