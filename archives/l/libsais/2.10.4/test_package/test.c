#include <stdio.h>
#include <string.h>
#include "libsais.h"

int main(void) {
    /* Minimal test: construct suffix array of "banana" */
    const uint8_t T[] = "banana";
    int32_t SA[6];
    int32_t n = 6;

    int32_t ret = libsais(T, SA, n, 0, NULL);
    if (ret != 0) {
        printf("FAIL: libsais returned %d\n", ret);
        return 1;
    }

    /* Suffix array of "banana" should be [5,3,1,0,4,2] */
    int32_t expected[] = {5, 3, 1, 0, 4, 2};
    for (int i = 0; i < n; i++) {
        if (SA[i] != expected[i]) {
            printf("FAIL: SA[%d]=%d, expected %d\n", i, SA[i], expected[i]);
            return 1;
        }
    }

    printf("test libsais 2.10.4: OK\n");
    return 0;
}
