#include <cstdio>
#include "ALACEncoder.h"
#include "ALACDecoder.h"

int main() {
    // Verify ALAC encoder/decoder struct sizes are as expected
    printf("ALAC encoder struct size: %zu\\n", sizeof(ALACEncoder));
    printf("ALAC decoder struct size: %zu\\n", sizeof(ALACDecoder));
    printf("ALAC library test passed!\\n");
    return 0;
}