/*
 * HarmonyOS-specific test for libxtrxdsp — Conan L1 test_package.
 *
 * File location:
 *   archives/l/libxtrxdsp/0.0.1-git20230203.271f5e6/test_package/test_ohos_dsp.c
 *
 * This program verifies the properties that are specific to this HarmonyOS
 * (OHOS / aarch64) adaptation of libxtrxdsp and that the generic consumer test
 * cannot cover:
 *
 *   1. The test really binds to the packaged artifact: the public entry points
 *      are resolvable through the process-wide symbol table (RTLD_DEFAULT),
 *      which the CI L1e destructive reverse check invalidates by moving the
 *      package's lib/ and include/ directories away.
 *
 *   2. The aarch64 code path is the intended one.  Upstream's CMakeLists.txt
 *      appends the x86 SIMD translation units (xtrxdsp_x86_sse2.c,
 *      xtrxdsp_x86_avx.c, xtrxdsp_x86_avx_fma.c) only when
 *      `ARCH MATCHES "^x86.*"`, and xtrxdsp_config.h defines
 *      XTRXDSP_HAS__SSE2__/__AVX__/__FMA__ only under
 *      `#if defined(__x86_64__) || defined(__i386__)`.  On OHOS/aarch64 the
 *      generic implementations must therefore be present and the x86 ones must
 *      be absent.  If a future change made the build try to compile the x86
 *      sources on aarch64, the -msse2/-mavx/-mfma compile flags would fail the
 *      build outright; this test additionally pins the resulting symbol set.
 *
 *   3. The public dispatcher resolves to exactly the implementation that the
 *      generic (`_no`) symbol exports, i.e. no dangling SIMD selection is left
 *      behind on this platform.
 *
 *   4. Byte order: the fast path of xtrxdsp_iq16_sc32() reinterprets the int16
 *      input as a 64-bit word and shifts the lanes out (v, v>>16, v>>32,
 *      v>>48).  That lane order is only correct on a little-endian target,
 *      which OHOS/aarch64 is; the check makes this platform assumption
 *      explicit instead of implicit.
 *
 *   5. The filter allocates its state with posix_memalign(64) and releases it
 *      in xtrxdsp_filter_free(); repeated init/free cycles must not fail,
 *      which catches allocator misuse on the target platform.
 *
 * A non-zero exit status means at least one assertion failed.
 */

#include <xtrxdsp.h>
#include <xtrxdsp_filters.h>

#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, what)                                                     \
    do {                                                                      \
        g_checks++;                                                           \
        if (!(cond)) {                                                        \
            g_failures++;                                                     \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, what);            \
        }                                                                     \
    } while (0)

#define CHECK_I(v, expected)                                                  \
    do {                                                                      \
        long _got = (long)(v);                                                \
        long _exp = (long)(expected);                                         \
        g_checks++;                                                           \
        if (_got != _exp) {                                                   \
            g_failures++;                                                     \
            fprintf(stderr, "FAIL line %d: %s = %ld, expected %ld\n",         \
                    __LINE__, #v, _got, _exp);                                \
        }                                                                     \
    } while (0)

/* Symbols provided by the shared library under test. */
static const char *const kRequiredSymbols[] = {
    "xtrxdsp_init",
    "xtrxdsp_sc32i_iq16",
    "xtrxdsp_sc32_iq16",
    "xtrxdsp_ic16i_iq16",
    "xtrxdsp_iq16_sc32",
    "xtrxdsp_iq16_sc32i",
    "xtrxdsp_iq16_ic16i",
    /* the generic aarch64 implementations */
    "xtrxdsp_sc32i_iq16_no",
    "xtrxdsp_sc32_iq16_no",
    "xtrxdsp_iq16_sc32_no",
};

/* x86-only SIMD entry points that must NOT be part of an aarch64 build. */
static const char *const kForbiddenSymbols[] = {
    "xtrxdsp_sc32i_iq16_sse2",
    "xtrxdsp_sc32i_iq16_avx",
    "xtrxdsp_iq16_sc32_sse2",
    "xtrxdsp_iq16_sc32_avx",
};

static void test_symbols(void)
{
    unsigned i;
    char msg[128];

    for (i = 0; i < sizeof(kRequiredSymbols) / sizeof(kRequiredSymbols[0]); i++) {
        void *p = dlsym(RTLD_DEFAULT, kRequiredSymbols[i]);
        snprintf(msg, sizeof(msg), "%s is not resolvable (test not bound to "
                 "the packaged library?)", kRequiredSymbols[i]);
        CHECK(p != NULL, msg);
    }

    for (i = 0; i < sizeof(kForbiddenSymbols) / sizeof(kForbiddenSymbols[0]); i++) {
        void *p = dlsym(RTLD_DEFAULT, kForbiddenSymbols[i]);
        snprintf(msg, sizeof(msg), "%s must not exist on OHOS/aarch64 "
                 "(x86 SIMD translation units were compiled?)",
                 kForbiddenSymbols[i]);
        CHECK(p == NULL, msg);
    }
}

/* The public dispatcher must select the generic implementation on aarch64. */
static void test_dispatch_matches_generic(void)
{
    float fi[4] = { 1.5f, -2.25f, 100.0f, -100.0f };
    float fq[4] = { -1.5f, 2.25f, -100.0f, 100.0f };
    int16_t via_public[8];
    int16_t via_generic[8];
    float in[4] = { 3.7f, -3.7f, 0.0f, 32767.0f };
    int16_t pub_iq[4];
    int16_t gen_iq[4];

    memset(via_public, 0x5A, sizeof(via_public));
    memset(via_generic, 0x5A, sizeof(via_generic));
    xtrxdsp_sc32i_iq16(fi, fq, via_public, 1.0f, sizeof(via_public));
    xtrxdsp_sc32i_iq16_no(fi, fq, via_generic, 1.0f, sizeof(via_generic));
    CHECK(memcmp(via_public, via_generic, sizeof(via_public)) == 0,
          "xtrxdsp_sc32i_iq16 != xtrxdsp_sc32i_iq16_no (duplicate symbol without public declaration)");

    memset(pub_iq, 0x5A, sizeof(pub_iq));
    memset(gen_iq, 0x5A, sizeof(gen_iq));
    xtrxdsp_sc32_iq16(in, pub_iq, 1.0f, sizeof(pub_iq));
    xtrxdsp_sc32_iq16_no(in, gen_iq, 1.0f, sizeof(gen_iq));
    CHECK(memcmp(pub_iq, gen_iq, sizeof(pub_iq)) == 0,
          "xtrxdsp_sc32_iq16 != xtrxdsp_sc32_iq16_no (duplicate symbol without public declaration)");

    /* and the values themselves are the documented ones */
    CHECK_I(via_public[0], 1);
    CHECK_I(via_public[1], -1);
    CHECK_I(pub_iq[0], 3);
    CHECK_I(pub_iq[1], -3);
}

/* Little-endian lane order of the 64-bit block load path. */
static void test_little_endian_lane_order(void)
{
    int16_t iq[4] = { 0x0102, 0x0304, 0x0506, 0x0708 };
    float out[4];
    uint64_t packed;
    unsigned i;
    int ok;

    CHECK(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
          "OHOS/aarch64 is expected to be little-endian");

    /* Rebuild the 64-bit word the way xtrxdsp_iq16_sc32()'s fast path reads
     * it: lane k lives in bits [16k, 16k+15). */
    packed = 0;
    for (i = 0; i < 4; i++)
        packed |= ((uint64_t)(uint16_t)iq[i]) << (16 * i);

    {
        const uint64_t *p = (const uint64_t *)(const void *)iq;
        CHECK(*p == packed, "host does not read the sample lanes little-endian");
    }

    memset(out, 0, sizeof(out));
    xtrxdsp_iq16_sc32(iq, out, 1.0f, sizeof(iq));

    ok = 1;
    for (i = 0; i < 4; i++)
        if (out[i] != (float)iq[i])
            ok = 0;
    CHECK(ok, "block fast path scrambled the sample lanes (endianness)");
}

/* posix_memalign(64) state must survive repeated allocation cycles. */
static void test_filter_alloc_cycles(void)
{
    float taps[64];
    xtrxdsp_filter_state_t st;
    unsigned cycle;
    int ok = 1;

    memset(taps, 0, sizeof(taps));
    taps[0] = 1.0f;

    for (cycle = 0; cycle < 16; cycle++) {
        memset(&st, 0, sizeof(st));
        if (xtrxdsp_filter_init(taps, 1, 0, 0, 512, &st) != 0) {
            ok = 0;
            break;
        }
        if (st.filter_taps == NULL || st.history_data == NULL) {
            ok = 0;
            xtrxdsp_filter_free(&st);
            break;
        }
        /* taps are replicated into the aligned block */
        if (st.filter_taps_float[0] != 1.0f) {
            ok = 0;
            xtrxdsp_filter_free(&st);
            break;
        }
        xtrxdsp_filter_free(&st);
    }
    CHECK(ok, "repeated xtrxdsp_filter_init/xtrxdsp_filter_free cycles failed");

    CHECK(st.filter_taps == NULL, "xtrxdsp_filter_free left filter_taps set");
    CHECK(st.history_data == NULL, "xtrxdsp_filter_free left history_data set");
}

int main(void)
{
    printf("libxtrxdsp HarmonyOS specific test\n");

    test_symbols();
    test_dispatch_matches_generic();
    test_little_endian_lane_order();
    test_filter_alloc_cycles();

    printf("checks: %d, failures: %d\n", g_checks, g_failures);
    if (g_failures != 0)
        return 1;
    printf("test_ohos_dsp: PASS\n");
    return 0;
}
