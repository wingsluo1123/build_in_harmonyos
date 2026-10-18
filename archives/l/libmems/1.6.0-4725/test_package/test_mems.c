/* Consumer test for libmems: exercises the real libMems C API in
 * libMems/twister.h (MT19937 generator shipped inside libMems-1.6).
 *
 * The alignment core headers (Match.h, Interval.h, MemHash.h, ...) all
 * require libGenome / libMUSCLE / Boost headers, so until the dependency
 * chain is published the dependency-free twister API is the runnable
 * consumer surface. Every check below calls into the installed library
 * (no print-only shell): a missing/incorrect libMems link fails the
 * build, a wrong generator fails an assertion, and main returns
 * non-zero unless all four checks pass.
 */
#include <stdio.h>

#include "libMems/twister.h"

static int g_passed = 0;
static int g_failed = 0;

static void check(int ok, const char *name) {
    if (ok) {
        ++g_passed;
        printf("CHECK-OK %s\n", name);
    } else {
        ++g_failed;
        printf("CHECK-FAIL %s\n", name);
    }
}

int main(void) {
    /* 1. Public MT19937 reference vector: init_genrand(5489) must yield
     * 3499211612 as its first output (Matsumoto/Nishimura reference).
     * SetTwisterSeed maps 1:1 to init_genrand. */
    SetTwisterSeed(5489UL);
    check(RandTwisterUnsigned() == 3499211612UL, "reference-vector-5489");

    /* 2. Determinism: reseeding reproduces the stream exactly. */
    SetTwisterSeed(2026UL);
    {
        unsigned first = RandTwisterUnsigned();
        SetTwisterSeed(2026UL);
        check(RandTwisterUnsigned() == first, "reseed-determinism");
    }

    /* 3. RandTwisterDouble is genrand_real1: closed interval [0, 1]. */
    SetTwisterSeed(7UL);
    {
        double d = RandTwisterDouble();
        check(d >= 0.0 && d <= 1.0, "double-range-01");
    }

    /* 4. CreateTwisterSeed produces a usable seed: seeding with it must
     * yield a valid stream (double inside [0, 1]). */
    {
        unsigned long seed = CreateTwisterSeed();
        SetTwisterSeed(seed);
        {
            double d = RandTwisterDouble();
            check(d >= 0.0 && d <= 1.0, "created-seed-stream");
        }
    }

    printf("RESULT: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 && g_passed == 4 ? 0 : 1;
}
