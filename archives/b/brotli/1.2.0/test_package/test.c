#include <stdio.h>
#include "brotli/decode.h"

int main(void) {
    printf("brotli version: %u\n", BrotliDecoderVersion());
    BrotliDecoderState *s = BrotliDecoderCreateState(NULL, NULL, NULL);
    if (s) { printf("decoder: OK\n"); BrotliDecoderDestroyState(s); }
    return 0;
}
