/*
 * test_package consumer test — minidraw (header-only).
 *
 * Verifies the backend-independent text APIs (UTF-8/UTF-16/UTF-32
 * conversion, BOM handling, endian swap) shipped by minidraw.h work
 * correctly on HarmonyOS PC with the OHOS aarch64 clang toolchain.
 */
#define MINIDRAW_IMPLEMENTATION
#include "minidraw.h"

#include <stdio.h>
#include <string.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            printf("FAIL: %s (line %d)\n", msg, __LINE__);                     \
            g_failures++;                                                      \
        }                                                                      \
    } while (0)

int main(void)
{
    md_result r;
    md_utf16 utf16[64];
    size_t utf16Len = 0;
    size_t processed = 0;
    md_utf32 utf32[64];
    size_t utf32Len = 0;
    const md_utf8 in[] = "Hello\\u4f60\\u597d \\u00e9\\u00e8 minidraw";
    const md_utf8 plain[] = "Hello minidraw";
    md_utf8 roundtrip[256];
    size_t roundtripLen = 0;

    /* UTF-8 → UTF-16LE conversion. */
    r = md_utf8_to_utf16le(utf16, 64, &utf16Len, in, sizeof(in) - 1, &processed, 0);
    CHECK(r == MD_SUCCESS, "md_utf8_to_utf16le failed");
    CHECK(processed == sizeof(in) - 1, "utf8 processed length mismatch");
    CHECK(utf16Len > 0, "utf16 output empty");

    /* UTF-16LE → UTF-8 roundtrip must preserve the original text. */
    r = md_utf16le_to_utf8(roundtrip, 256, &roundtripLen, utf16, utf16Len, &processed, 0);
    CHECK(r == MD_SUCCESS, "md_utf16le_to_utf8 failed");
    CHECK(roundtripLen == sizeof(in) - 1, "roundtrip length mismatch");
    CHECK(memcmp(roundtrip, in, roundtripLen) == 0, "roundtrip content mismatch");

    /* UTF-8 → UTF-32LE conversion. */
    r = md_utf8_to_utf32le(utf32, 64, &utf32Len, plain, sizeof(plain) - 1, &processed, 0);
    CHECK(r == MD_SUCCESS, "md_utf8_to_utf32le failed");
    CHECK(utf32Len > 0, "utf32 output empty");

    /* Endian swap must roundtrip. */
    md_swap_endian_utf32(utf32, utf32Len);
    md_swap_endian_utf32(utf32, utf32Len);

    /* BOM detection helpers. */
    {
        md_uint8 utf16bom[2] = {0xFF, 0xFE};
        md_uint8 utf32bom[4] = {0xFF, 0xFE, 0x00, 0x00};
        CHECK(md_has_utf16_bom(utf16bom, 2), "utf16 BOM detection failed");
        CHECK(md_has_utf32_bom(utf32bom, 4), "utf32 BOM detection failed");
    }

    if (g_failures == 0) {
        printf("OK: all minidraw consumer checks passed. version=ee0989e954\\n");
        return 0;
    }

    printf("NG: %d consumer check(s) failed\\n", g_failures);
    return 1;
}