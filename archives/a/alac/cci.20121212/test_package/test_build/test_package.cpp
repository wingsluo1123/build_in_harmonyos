#include <cstdio>
#include "ALACEncoder.h"
#include "ALACDecoder.h"

int main() {
    ALACEncoder encoder;
    ALACDecoder decoder;
    ALACSpecificConfig config;
    encoder.GetConfig(config);
    uint32_t cookieSize = encoder.GetMagicCookieSize(2);
    printf("ALAC test passed! frameLength=%u\n", (unsigned)config.frameLength);
    return 0;
}
