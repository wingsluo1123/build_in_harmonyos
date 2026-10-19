#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "base64.h"

/* Real consumer test: encode -> integrity check -> decode -> round-trip compare.
   Exercises the public base64()/unbase64()/base64integrity() API from the
   installed package headers and linked library (R34: no empty-shell tests). */
int main(void) {
    const char* original = "HarmonyOS PC consumer test of nibbleandahalf @#$%^&*() 中文";
    int encoded_len = 0;
    int recovered_len = 0;

    char* encoded = base64(original, (int)strlen(original), &encoded_len);
    if (!encoded || encoded_len <= 0) {
        fprintf(stderr, "FAIL: base64() returned NULL or empty (len=%d)\n", encoded_len);
        return 1;
    }
    if (!base64integrity(encoded, encoded_len)) {
        fprintf(stderr, "FAIL: base64integrity() rejected valid base64 string\n");
        free(encoded);
        return 1;
    }
    unsigned char* recovered = unbase64(encoded, encoded_len, &recovered_len);
    if (!recovered || recovered_len != (int)strlen(original)) {
        fprintf(stderr, "FAIL: unbase64() length mismatch (got %d, want %d)\n",
                recovered_len, (int)strlen(original));
        free(encoded);
        return 1;
    }
    if (memcmp(recovered, original, (size_t)recovered_len) != 0) {
        fprintf(stderr, "FAIL: round-trip data mismatch\n");
        free(encoded);
        free(recovered);
        return 1;
    }
    printf("PASS: round-trip ok, %d bytes -> %d base64 chars -> %d bytes\n",
           (int)strlen(original), encoded_len, recovered_len);
    free(encoded);
    free(recovered);
    return 0;
}
