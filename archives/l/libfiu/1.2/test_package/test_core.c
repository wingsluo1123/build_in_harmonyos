/* test_core.c — libfiu core API consumer test (R34: real API calls).
 *
 * Covers: fiu_init, fiu_fail on never-enabled points, fiu_enable with
 * failnum/failinfo, fiu_failinfo, fiu_disable, FIU_ONETIME semantics and
 * the fiu_return_on helper macro. Exits non-zero on the first mismatch so
 * a hollow/stub library can never report PASS.
 */
#include <stdio.h>
#include <fiu.h>
#include <fiu-control.h>

static int failures = 0;

#define CHECK(cond, label) do { \
    if (!(cond)) { \
        printf("CORE-FAIL: %s (line %d)\n", label, __LINE__); \
        failures++; \
    } else { \
        printf("CORE-OK: %s\n", label); \
    } \
} while (0)

static int marker_value;

static int returns_minus_one_when_failing(void)
{
    fiu_return_on("hmbs_core_macro", -1);
    return 0;
}

int main(void)
{
    static int sentinel = 12345;

    CHECK(fiu_init(0) == 0, "fiu_init returns 0");
    CHECK(fiu_fail("hmbs_never_enabled_xyz") == 0, "never-enabled point does not fail");

    CHECK(fiu_enable("hmbs_core", 7, &sentinel, 0) == 0, "fiu_enable hmbs_core");
    CHECK(fiu_fail("hmbs_core") == 7, "enabled point returns failnum 7");
    CHECK(fiu_failinfo() == &sentinel, "failinfo pointer round-trips");

    CHECK(fiu_disable("hmbs_core") == 0, "fiu_disable hmbs_core");
    CHECK(fiu_fail("hmbs_core") == 0, "disabled point does not fail");

    CHECK(fiu_enable("hmbs_core_once", 3, NULL, FIU_ONETIME) == 0, "fiu_enable onetime");
    CHECK(fiu_fail("hmbs_core_once") != 0, "onetime point fails once");
    CHECK(fiu_fail("hmbs_core_once") == 0, "onetime point auto-disabled");

    CHECK(fiu_enable("hmbs_core_macro", 1, NULL, 0) == 0, "fiu_enable macro point");
    marker_value = returns_minus_one_when_failing();
    CHECK(marker_value == -1, "fiu_return_on returns -1 when failing");
    CHECK(fiu_disable("hmbs_core_macro") == 0, "fiu_disable macro point");
    marker_value = returns_minus_one_when_failing();
    CHECK(marker_value == 0, "helper returns 0 when not failing");

    if (failures == 0) {
        printf("CORE-TEST-PASS: 14 checks passed\n");
        return 0;
    }
    printf("CORE-TEST-FAIL: %d checks failed\n", failures);
    return 1;
}
