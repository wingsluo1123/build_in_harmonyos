/* test_control.c — libfiu control API consumer test (R34: real API calls).
 *
 * Covers: fiu_set_prng_seed, fiu_enable_random (probability 1.0 and 0.0),
 * fiu_enable_external with pass/fail callbacks, and a second independent
 * point enable/disable cycle. Exits non-zero on the first mismatch.
 */
#include <stdio.h>
#include <fiu.h>
#include <fiu-control.h>

static int failures = 0;

#define CHECK(cond, label) do { \
    if (!(cond)) { \
        printf("CONTROL-FAIL: %s (line %d)\n", label, __LINE__); \
        failures++; \
    } else { \
        printf("CONTROL-OK: %s\n", label); \
    } \
} while (0)

static int cb_fail(const char *name, int *failnum, void **failinfo, unsigned int *flags)
{
    (void)name;
    (void)failnum;
    (void)failinfo;
    (void)flags;
    return 1;
}

static int cb_ok(const char *name, int *failnum, void **failinfo, unsigned int *flags)
{
    (void)name;
    (void)failnum;
    (void)failinfo;
    (void)flags;
    return 0;
}

int main(void)
{
    fiu_set_prng_seed(42u);
    CHECK(fiu_init(0) == 0, "fiu_init after set_prng_seed");

    CHECK(fiu_enable_random("hmbs_rand_always", 5, NULL, 0, 1.0f) == 0,
        "enable_random prob 1.0");
    CHECK(fiu_fail("hmbs_rand_always") != 0, "prob-1.0 point fails");
    CHECK(fiu_disable("hmbs_rand_always") == 0, "disable rand point");

    CHECK(fiu_enable_random("hmbs_rand_never", 5, NULL, 0, 0.0f) == 0,
        "enable_random prob 0.0");
    CHECK(fiu_fail("hmbs_rand_never") == 0, "prob-0.0 point does not fail");
    CHECK(fiu_disable("hmbs_rand_never") == 0, "disable rand-never point");

    CHECK(fiu_enable_external("hmbs_ext_fail", 9, NULL, 0, cb_fail) == 0,
        "enable_external fail-callback");
    CHECK(fiu_fail("hmbs_ext_fail") != 0, "external fail-callback fails");
    CHECK(fiu_disable("hmbs_ext_fail") == 0, "disable ext-fail point");

    CHECK(fiu_enable_external("hmbs_ext_ok", 9, NULL, 0, cb_ok) == 0,
        "enable_external ok-callback");
    CHECK(fiu_fail("hmbs_ext_ok") == 0, "external ok-callback does not fail");
    CHECK(fiu_disable("hmbs_ext_ok") == 0, "disable ext-ok point");

    CHECK(fiu_enable("hmbs_second", 3, NULL, 0) == 0, "enable second point");
    CHECK(fiu_fail("hmbs_second") == 3, "second point returns failnum 3");
    CHECK(fiu_disable("hmbs_second") == 0, "disable second point");
    CHECK(fiu_fail("hmbs_second") == 0, "second point quiet after disable");

    if (failures == 0) {
        printf("CONTROL-TEST-PASS: 17 checks passed\n");
        return 0;
    }
    printf("CONTROL-TEST-FAIL: %d checks failed\n", failures);
    return 1;
}
