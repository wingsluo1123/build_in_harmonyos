/* test_package consumer for sigutils 0.3.0 (HarmonyOS PC).
 *
 * 6 real, offline, deterministic assertions against the installed
 * libsigutils (linked directly with CC, mirroring upstream sigutils.pc
 * consumer flags). Expected values derived from library semantics:
 *  - su_ncqo freq unit: omega = PI * fnor (sigutils/sampling.h
 *    SU_NORM2ANG_FREQ); constant oscillator check mirrors upstream
 *    src/tests/ncqo.c final block (freq 0, phase 0 -> read_i == 1).
 *  - su_iir_bwlpf_init(5, 0.25): 5th-order digital Butterworth LPF with
 *    cutoff omega_c = PI * 0.25 (analytic |H| checked with the exact
 *    upstream coefficient formulas: |H(0.3927)| = 0.9997,
 *    |H(4.7124->alias 1.5708)| = 0.0122).
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sigutils/sigutils.h>
#include <sigutils/ncqo.h>
#include <sigutils/iir.h>
#include <sigutils/version.h>

#define CHECK(n, cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "check %d FAILED: %s (line %d)\n", n, #cond, __LINE__); \
        return 10 + (n); \
    } \
    printf("check %d ok\n", n); \
} while (0)

#define TONE_N   1024
#define TAIL_N   256

static double tail_rms(const SUCOMPLEX *buf) {
    double acc = 0.0;
    int i;
    for (i = TONE_N - TAIL_N; i < TONE_N; i++) {
        double re = (double) SU_C_REAL(buf[i]);
        acc += re * re;
    }
    return sqrt(acc / TAIL_N);
}

int main(void) {
    int i;

    /* 1: ABI handshake -- runtime ABI matches the headers we compile
     * against; sigutils_abi_check() aborts the process on mismatch. */
    CHECK(1, sigutils_abi_version() == SIGUTILS_ABI_VERSION
             && SIGUTILS_ABI_VERSION == 1);
    sigutils_abi_check(SIGUTILS_ABI_VERSION);

    /* 2: library init + exact version string (non-degenerate). */
    CHECK(2, su_lib_init() == SU_TRUE
             && sigutils_api_version() != NULL
             && strcmp(sigutils_api_version(), "0.3.0") == 0);
    printf("sigutils api version: %s\n", sigutils_api_version());

    /* 3: NCQO constant oscillator: freq 0, phase 0 -> in-phase reads are
     * exactly 1, quadrature exactly 0 (upstream ncqo.c final block). */
    {
        su_ncqo_t nco = su_ncqo_INITIALIZER;
        su_ncqo_init(&nco, 1);
        su_ncqo_set_freq(&nco, 0);
        su_ncqo_set_phase(&nco, 0);
        for (i = 0; i < 64; i++) {
            if (fabs(su_ncqo_read_i(&nco) - 1) > 1e-4
                    || fabs(su_ncqo_read_q(&nco)) > 1e-4) {
                fprintf(stderr, "check 3 FAILED at sample %d\n", i);
                return 13;
            }
        }
        printf("check 3 ok\n");
    }

    /* 4: NCQO unity tone at fnor=1 (omega=PI): read_i alternates exactly
     * between -1 and +1, so mean ~ 0 and peak-to-peak ~ 2. */
    {
        su_ncqo_t nco = su_ncqo_INITIALIZER;
        double sum = 0.0, mn = 1e9, mx = -1e9;
        su_ncqo_init(&nco, 1);
        for (i = 0; i < 512; i++) {
            SUFLOAT v = su_ncqo_read_i(&nco);
            sum += v;
            if (v < mn) mn = v;
            if (v > mx) mx = v;
        }
        CHECK(4, fabs(sum / 512) < 0.05 && (mx - mn) > 1.9);
    }

    /* 5-6: Butterworth LPF (order 5, fc=0.25) real frequency selectivity
     * on complex input: passband tone (fnor=0.125, omega=0.3927) passes
     * with |H|~1 (tail RMS of real part ~ 0.707), stopband tone
     * (fnor=1.5, omega=4.7124, aliases to 1.5708) is attenuated to
     * |H|~0.012 (tail RMS ~ 0.009). Catches zero-stub filters and
     * pass-through stubs alike. */
    {
        SUCOMPLEX buf[TONE_N];
        su_ncqo_t nco;
        su_iir_filt_t lpf = su_iir_filt_INITIALIZER;
        double rms;

        CHECK(5, su_iir_bwlpf_init(&lpf, 5, 0.25) == SU_TRUE);
        su_ncqo_init(&nco, 0.125);
        for (i = 0; i < TONE_N; i++)
            buf[i] = su_iir_filt_feed(&lpf, su_ncqo_read(&nco));
        su_iir_filt_finalize(&lpf);
        rms = tail_rms(buf);
        printf("passband tail rms: %f\n", rms);
        CHECK(5, rms > 0.6 && rms < 0.75);

        CHECK(6, su_iir_bwlpf_init(&lpf, 5, 0.25) == SU_TRUE);
        su_ncqo_init(&nco, 1.5);
        for (i = 0; i < TONE_N; i++)
            buf[i] = su_iir_filt_feed(&lpf, su_ncqo_read(&nco));
        su_iir_filt_finalize(&lpf);
        rms = tail_rms(buf);
        printf("stopband tail rms: %f\n", rms);
        CHECK(6, rms < 0.1);
    }

    printf("sigutils API assertions: 6 passed\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
           "\"command\":\"./test_sigutils\",\"discovered\":6,"
           "\"passedCount\":6}\n");
    return 0;
}
