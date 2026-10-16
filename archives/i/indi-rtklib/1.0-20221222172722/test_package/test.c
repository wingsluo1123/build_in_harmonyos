// indi-rtklib consumer test (R34: exercises the real public C API).
// The package ships the rtkrcv_parser module; we vendor-compile it and call
// scansolution() — the parser the driver uses to read RTK solution strings.
//
// Real-behavior notes (measured, not assumed):
//   - Patch 0004 backports upstream master's strcmp -> strncmp fix: the
//     snapshot's char status[6] + sscanf("(%6c)") writes exactly 6 bytes with
//     no terminator, so strcmp depended on stack garbage past the buffer (UB;
//     on musl no status ever matched and *fix kept its previous value).
//   - With strncmp every status name resolves deterministically, including
//     the short names "FIX"/"FLOAT" that the unpatched parser never matched.
#include <stdio.h>
#include <string.h>
#include "rtkrcv_parser.h"

static int failures = 0;

#define CHECK(cond)                                              \
    do {                                                         \
        if (!(cond)) {                                           \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);\
            ++failures;                                          \
        }                                                        \
    } while (0)

int main(void)
{
    char flags, type;
    double dms[3] = {0}, timestamp = 0;
    enum rtkrcv_fix_status fix;

    // no-fix sentinel "------" -> status_no_fix
    char s_no[RTKRCV_MAX_LENGTH] = "(------) A:0.0 R:0.0 N:0";
    scansolution(s_no, &flags, &type, dms, &fix, &timestamp);
    printf("no_fix: fix=%d (expect %d)\n", (int)fix, (int)status_no_fix);
    CHECK(fix == status_no_fix);

    // "SINGLE" is 6 chars -> status_single
    char s_single[RTKRCV_MAX_LENGTH] = "(SINGLE) A:1.0 R:2.0 N:5";
    scansolution(s_single, &flags, &type, dms, &fix, &timestamp);
    printf("single: fix=%d (expect %d)\n", (int)fix, (int)status_single);
    CHECK(fix == status_single);

    // short names resolve via strncmp prefix match (post-0004) -> status_fix
    char s_fix[RTKRCV_MAX_LENGTH] = "(FIX) A:1.0 R:2.0 N:5";
    scansolution(s_fix, &flags, &type, dms, &fix, &timestamp);
    printf("fix: fix=%d (expect %d)\n", (int)fix, (int)status_fix);
    CHECK(fix == status_fix);

    // "FLOAT" must not be swallowed by the earlier "FIX" branch -> status_float
    char s_float[RTKRCV_MAX_LENGTH] = "(FLOAT) A:1.0 R:2.0 N:5";
    scansolution(s_float, &flags, &type, dms, &fix, &timestamp);
    printf("float: fix=%d (expect %d)\n", (int)fix, (int)status_float);
    CHECK(fix == status_float);

    if (failures == 0) {
        printf("PASS: scansolution public C API exercised\n");
        return 0;
    }
    printf("FAILED: %d checks\n", failures);
    return 1;
}
