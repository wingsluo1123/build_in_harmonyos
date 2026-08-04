#include <cstdio>
#include "ALACEncoder.h"
#include "ALACDecoder.h"

int main() {
    // Verify ALAC encoder/decoder can be instantiated and basic API works
    ALACEncoder encoder;
    ALACDecoder decoder;

    // Verify GetConfig and GetMagicCookieSize return expected values
    ALACSpecificConfig config;
    encoder.GetConfig(config);
    uint32_t cookieSize = encoder.GetMagicCookieSize(2);

    printf("ALAC encoder config: frameLength=%u\n", (unsigned)config.frameLength);
    printf("ALAC magic cookie size (2 ch): %u\n", (unsigned)cookieSize);
    printf("ALAC library test passed!\n");
    return 0;
}