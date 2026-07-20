#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lzma.h>

int main(void)
{
    static const char input[] = "OpenHarmony static liblzma round-trip test";
    unsigned char compressed[256];
    unsigned char decoded[sizeof(input)] = {0};
    size_t compressed_size = 0;
    size_t input_position = 0;
    size_t decoded_size = 0;
    uint64_t memory_limit = UINT64_MAX;

    if (lzma_easy_buffer_encode(LZMA_PRESET_DEFAULT, LZMA_CHECK_CRC64, NULL,
            (const uint8_t *)input, sizeof(input), compressed, &compressed_size,
            sizeof(compressed)) != LZMA_OK) {
        fputs("liblzma compression failed\n", stderr);
        return 1;
    }

    if (lzma_stream_buffer_decode(&memory_limit, 0, NULL, compressed,
            &input_position, compressed_size, decoded, &decoded_size,
            sizeof(decoded)) != LZMA_OK) {
        fputs("liblzma decompression failed\n", stderr);
        return 1;
    }

    if (decoded_size != sizeof(input) || memcmp(input, decoded, sizeof(input)) != 0) {
        fputs("liblzma round-trip mismatch\n", stderr);
        return 1;
    }

    puts("static liblzma round-trip: OK");
    return 0;
}
