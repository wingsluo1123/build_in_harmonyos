/*
 * test.c — farbfeld format test helper
 *
 * Generates a minimal 1x1 farbfeld image to stdout.
 * Usage: ./test_farbfeld > test.ff
 *
 * farbfeld format:
 *   magic: "farbfeld" (8 bytes)
 *   width: uint32 big-endian
 *   height: uint32 big-endian
 *   pixels: 16-bit RGBA per channel, big-endian, row-major
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>

int main(void) {
    /* Write farbfeld header */
    fwrite("farbfeld", 1, 8, stdout);

    /* Width=1, Height=1 (big-endian) */
    uint32_t w = htonl(1), h = htonl(1);
    fwrite(&w, 4, 1, stdout);
    fwrite(&h, 4, 1, stdout);

    /* Pixel: R=0, G=0, B=0, A=65535 (16-bit big-endian each) */
    uint16_t r = htons(0), g = htons(0), b = htons(0), a = htons(65535);
    fwrite(&r, 2, 1, stdout);
    fwrite(&g, 2, 1, stdout);
    fwrite(&b, 2, 1, stdout);
    fwrite(&a, 2, 1, stdout);

    return 0;
}
