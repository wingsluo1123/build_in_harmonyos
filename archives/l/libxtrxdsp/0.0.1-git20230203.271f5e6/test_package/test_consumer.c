/*
 * Consumer integration test for libxtrxdsp — Conan L1 test_package.
 *
 * File location:
 *   archives/l/libxtrxdsp/0.0.1-git20230203.271f5e6/test_package/test_consumer.c
 *
 * This program links the *installed* libxtrxdsp and exercises the public API
 * against values that are derived from the documented conversion contract and
 * from the upstream template implementations, so every assertion has a single
 * deterministic expected result:
 *
 *   * xtrxdsp_sc32i_iq16 / xtrxdsp_sc32_iq16 / xtrxdsp_ic16i_iq16
 *       float <-> int16 sample conversion, truncation towards zero,
 *       interleaving / de-interleaving of the I and Q lanes.
 *   * xtrxdsp_iq16_sc32 / xtrxdsp_iq16_sc32i
 *       the 64-bit block fast path (little-endian lane order) plus the
 *       non-multiple-of-8 tail path, both against the same expectations.
 *   * xtrxdsp_iq16_ic16i
 *       int16 I/Q de-interleaving.
 *   * xtrxdsp_filter_init / xtrxdsp_filter_initi / xtrxdsp_filter_work /
 *     xtrxdsp_filter_free
 *       the full parameter-validation contract (-EINVAL cases), the documented
 *       return value (num_insamples >> decim) and the actual FIR behaviour:
 *       a 1-tap all-pass filter with inter=0 is a pure copy of the input
 *       delayed by history_size (= 2 * MAX_TAPS = 128) floats.
 *
 * The program has no dependency on XTRX hardware, on a device node, or on any
 * network resource, so it is deterministic on any host.
 *
 * A non-zero exit status means at least one assertion failed.
 */

#include <xtrxdsp.h>
#include <xtrxdsp_filters.h>

#include <errno.h>
#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failures = 0;

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

#define CHECK_F(v, expected)                                                  \
    do {                                                                      \
        float _got = (v);                                                     \
        float _exp = (float)(expected);                                       \
        g_checks++;                                                           \
        if (_got != _exp) {                                                   \
            g_failures++;                                                     \
            fprintf(stderr, "FAIL line %d: %s = %g, expected %g\n",           \
                    __LINE__, #v, (double)_got, (double)_exp);                \
        }                                                                     \
    } while (0)

/* Compare a whole vector, counting it as one check. */
static void check_vectors(const float *got, const float *exp, unsigned n,
                          const char *what)
{
    unsigned i;
    int bad = 0;

    g_checks++;
    for (i = 0; i < n; i++) {
        if (got[i] != exp[i]) {
            if (bad < 4)
                fprintf(stderr, "FAIL %s[%u] = %g, expected %g\n", what, i,
                        (double)got[i], (double)exp[i]);
            bad++;
        }
    }
    if (bad) {
        g_failures++;
        fprintf(stderr, "FAIL %s: %d of %u elements differ\n", what, bad, n);
    }
}

/* ── 1. float -> int16 interleaved conversion (sc32i_iq16) ── */

static void test_sc32i_iq16(void)
{
    float fi[4] = { 1.5f, -2.25f, 100.0f, -100.0f };
    float fq[4] = { -1.5f, 2.25f, -100.0f, 100.0f };
    int16_t out[8];
    float si[1] = { 1.5f };
    float sq[1] = { -1.5f };
    int16_t so[2];

    memset(out, 0x5A, sizeof(out));
    xtrxdsp_sc32i_iq16(fi, fq, out, 1.0f, sizeof(out));

    /* The two lanes are interleaved I,Q,I,Q and each float is truncated
     * towards zero by the int16_t conversion. */
    CHECK_I(out[0], 1);      /* (int16_t)  1.5  */
    CHECK_I(out[1], -1);     /* (int16_t) -1.5  */
    CHECK_I(out[2], -2);     /* (int16_t) -2.25 */
    CHECK_I(out[3], 2);
    CHECK_I(out[4], 100);
    CHECK_I(out[5], -100);
    CHECK_I(out[6], -100);
    CHECK_I(out[7], 100);

    /* scale is applied before the conversion */
    xtrxdsp_sc32i_iq16(si, sq, so, 2.0f, sizeof(so));
    CHECK_I(so[0], 3);       /* (int16_t) (1.5 * 2)  */
    CHECK_I(so[1], -3);      /* (int16_t) (-1.5 * 2) */
}

/* ── 2. float -> int16 interleaved conversion (sc32_iq16) ── */

static void test_sc32_iq16(void)
{
    float in[4] = { 3.7f, -3.7f, 0.0f, 32767.0f };
    int16_t o[4];

    memset(o, 0x5A, sizeof(o));
    xtrxdsp_sc32_iq16(in, o, 1.0f, sizeof(o));

    CHECK_I(o[0], 3);        /* truncation towards zero, not rounding */
    CHECK_I(o[1], -3);
    CHECK_I(o[2], 0);
    CHECK_I(o[3], 32767);
}

/* ── 3. int16 I/Q re-interleaving (ic16i_iq16) ── */

static void test_ic16i_iq16(void)
{
    int16_t ii[2] = { 11, -12 };
    int16_t qq[2] = { 21, -22 };
    int16_t oo[4];

    memset(oo, 0x5A, sizeof(oo));
    xtrxdsp_ic16i_iq16(ii, qq, oo, sizeof(oo));

    CHECK_I(oo[0], 11);
    CHECK_I(oo[1], 21);
    CHECK_I(oo[2], -12);
    CHECK_I(oo[3], -22);
}

/* ── 4. int16 -> float conversion, block fast path and tail path ── */

static void test_iq16_sc32(void)
{
    int16_t iq[8] = { 1, -2, 3, -4, 32767, -32768, 100, -100 };
    int16_t iq6[6] = { 1, -2, 3, -4, 5, -6 };
    float exp8[8];
    float exp6[6];
    float fo[8];
    float fo6[6];
    float fs[4];
    unsigned i;

    for (i = 0; i < 8; i++)
        exp8[i] = (float)iq[i];
    for (i = 0; i < 6; i++)
        exp6[i] = (float)iq6[i];

    /* 16 input bytes -> two 8-byte blocks (the 64-bit load path) */
    memset(fo, 0, sizeof(fo));
    xtrxdsp_iq16_sc32(iq, fo, 1.0f, sizeof(iq));
    check_vectors(fo, exp8, 8, "iq16_sc32(block)");

    /* 12 input bytes -> one 8-byte block + a 4-byte tail */
    memset(fo6, 0, sizeof(fo6));
    xtrxdsp_iq16_sc32(iq6, fo6, 1.0f, sizeof(iq6));
    check_vectors(fo6, exp6, 6, "iq16_sc32(tail)");

    /* scale is applied to every sample */
    xtrxdsp_iq16_sc32(iq, fs, 0.5f, 4 * (int)sizeof(int16_t));
    CHECK_F(fs[0], 0.5f);    /*  1 * 0.5 */
    CHECK_F(fs[1], -1.0f);   /* -2 * 0.5 */
    CHECK_F(fs[2], 1.5f);    /*  3 * 0.5 */
    CHECK_F(fs[3], -2.0f);   /* -4 * 0.5 */
}

/* ── 5. int16 -> float de-interleaving (iq16_sc32i) ── */

static void test_iq16_sc32i(void)
{
    int16_t diq[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
    float da[4];
    float db[4];
    float expa[4] = { 1.0f, 3.0f, 5.0f, 7.0f };
    float expb[4] = { 2.0f, 4.0f, 6.0f, 8.0f };

    memset(da, 0, sizeof(da));
    memset(db, 0, sizeof(db));
    xtrxdsp_iq16_sc32i(diq, da, db, 1.0f, sizeof(diq));

    check_vectors(da, expa, 4, "iq16_sc32i(I)");
    check_vectors(db, expb, 4, "iq16_sc32i(Q)");
}

/* ── 6. int16 de-interleaving (iq16_ic16i) ── */

static void test_iq16_ic16i(void)
{
    int16_t ciq[4] = { 10, 20, 30, 40 };
    int16_t ca[2];
    int16_t cb[2];

    memset(ca, 0x5A, sizeof(ca));
    memset(cb, 0x5A, sizeof(cb));
    xtrxdsp_iq16_ic16i(ciq, ca, cb, sizeof(ciq));

    CHECK_I(ca[0], 10);
    CHECK_I(cb[0], 20);
    CHECK_I(ca[1], 30);
    CHECK_I(cb[1], 40);
}

/* ── 7. FIR channel filter: validation contract + all-pass behaviour ── */

#define TAP_COUNT   64          /* upstream MAX_TAPS */
#define BLOCK       512         /* >= history_size (2 * MAX_TAPS = 128) */
#define HIST        128         /* 2 * MAX_TAPS, in floats */

static void fill_block(float *buf, float base)
{
    unsigned k;

    for (k = 0; k < BLOCK / 2; k++) {
        buf[2 * k] = base + (float)k * 0.5f;
        buf[2 * k + 1] = -(base + (float)k * 0.25f);
    }
}

static void test_filters(void)
{
    float taps[TAP_COUNT];
    int16_t itaps[TAP_COUNT];
    xtrxdsp_filter_state_t st;
    float in[BLOCK];
    float in2[BLOCK];
    float out[BLOCK];
    float out2[BLOCK];
    unsigned i;
    unsigned produced;

    memset(taps, 0, sizeof(taps));
    taps[0] = 1.0f;                       /* 1-tap all-pass FIR */
    memset(itaps, 0, sizeof(itaps));
    itaps[0] = 32767;

    /* --- parameter validation (-EINVAL contract from the filter core) --- */
    CHECK_I(xtrxdsp_filter_init(taps, TAP_COUNT + 1, 0, 0, HIST, &st),
            -EINVAL);                     /* count > MAX_TAPS */
    CHECK_I(xtrxdsp_filter_init(taps, 1, 0, 3, HIST, &st),
            -EINVAL);                     /* inter > 2 */
    CHECK_I(xtrxdsp_filter_init(taps, 1, 7, 0, HIST, &st),
            -EINVAL);                     /* decim > 6 */
    CHECK_I(xtrxdsp_filter_init(taps, TAP_COUNT, 0, 0, TAP_COUNT - 1, &st),
            -EINVAL);                     /* max_sps_block < count */

    /* --- valid initialisation --- */
    memset(&st, 0, sizeof(st));
    CHECK_I(xtrxdsp_filter_init(taps, 1, 0, 0, BLOCK, &st), 0);

    memset(out, 0x5A, sizeof(out));
    fill_block(in, 0.0f);

    /* decim=0, inter=0 -> one output sample set per input sample set */
    produced = xtrxdsp_filter_work(&st, in, out, BLOCK);
    CHECK_I(produced, BLOCK);

    /* The history is primed with zeros, so the first history_size floats of
     * the output are zero ... */
    for (i = 0; i < HIST; i++) {
        if (out[i] != 0.0f) {
            g_checks++;
            g_failures++;
            fprintf(stderr, "FAIL filter warm-up: out[%u] = %g, expected 0\n",
                    i, (double)out[i]);
            break;
        }
    }
    g_checks++;

    /* ... and the rest is the input delayed by exactly history_size floats
     * (BLOCK - HIST floats are emitted; the last HIST floats stay in the
     * filter history for the next call). */
    for (i = 0; i < BLOCK - HIST; i++) {
        if (out[HIST + i] != in[i]) {
            g_checks++;
            g_failures++;
            fprintf(stderr,
                    "FAIL filter pass-through: out[%u] = %g, expected in[%u] = %g\n",
                    HIST + i, (double)out[HIST + i], i, (double)in[i]);
            break;
        }
    }
    g_checks++;

    /* Second call must continue the same delayed stream: the first
     * history_size floats are the tail of the previous block. */
    fill_block(in2, 100.0f);
    memset(out2, 0x5A, sizeof(out2));
    produced = xtrxdsp_filter_work(&st, in2, out2, BLOCK);
    CHECK_I(produced, BLOCK);

    for (i = 0; i < HIST; i++) {
        if (out2[i] != in[BLOCK - HIST + i]) {
            g_checks++;
            g_failures++;
            fprintf(stderr,
                    "FAIL filter continuity: out2[%u] = %g, expected %g\n",
                    i, (double)out2[i], (double)in[BLOCK - HIST + i]);
            break;
        }
    }
    g_checks++;

    for (i = 0; i < BLOCK - HIST; i++) {
        if (out2[HIST + i] != in2[i]) {
            g_checks++;
            g_failures++;
            fprintf(stderr,
                    "FAIL filter pass-through (2nd): out2[%u] = %g, expected in2[%u] = %g\n",
                    HIST + i, (double)out2[HIST + i], i, (double)in2[i]);
            break;
        }
    }
    g_checks++;

    /* decim=1 -> half the sample sets are produced */
    xtrxdsp_filter_free(&st);
    memset(&st, 0, sizeof(st));
    CHECK_I(xtrxdsp_filter_init(taps, 1, 1, 0, BLOCK, &st), 0);
    memset(out, 0x5A, sizeof(out));
    produced = xtrxdsp_filter_work(&st, in, out, BLOCK);
    CHECK_I(produced, BLOCK >> 1);
    xtrxdsp_filter_free(&st);

    /* the integer-tap variant shares the same core */
    memset(&st, 0, sizeof(st));
    CHECK_I(xtrxdsp_filter_initi(itaps, 1, 0, 0, BLOCK, &st), 0);
    memset(out, 0x5A, sizeof(out));
    produced = xtrxdsp_filter_worki(&st, (const int16_t *)in, (int16_t *)out,
                                    BLOCK);
    CHECK_I(produced, BLOCK);

    /* free releases the aligned block and clears both pointers */
    xtrxdsp_filter_free(&st);
    CHECK_I(st.filter_taps == NULL, 1);
    CHECK_I(st.history_data == NULL, 1);
}

int main(void)
{
    printf("libxtrxdsp consumer integration test\n");

    test_sc32i_iq16();
    test_sc32_iq16();
    test_ic16i_iq16();
    test_iq16_sc32();
    test_iq16_sc32i();
    test_iq16_ic16i();
    test_filters();

    printf("checks: %d, failures: %d\n", g_checks, g_failures);
    if (g_failures != 0)
        return 1;
    printf("test_consumer: PASS\n");
    return 0;
}
