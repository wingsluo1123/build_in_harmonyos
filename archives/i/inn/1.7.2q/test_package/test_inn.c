/* Consumer test for inn/1.7.2q: link libinn.a and exercise three real
 * subsystems — wildmat(1) pattern matching, Radix32 encoding and the
 * parsedate date parser (plus INNVersion/GetTimeInfo). 20 assertions;
 * exits non-zero on the first failure so the harness can tell pass
 * from fail by the exit code alone.
 *
 * Include order follows the upstream canonical pattern (e.g. expire/convdate.c):
 * <sys/types.h> + configdata.h + clibrary.h before libinn.h. clibrary.h
 * defines PID_T (typedef pid_t PID_T) used by libinn.h waitnb(); including
 * libinn.h alone fails with "unknown type name PID_T". */
#include <stdio.h>
#include <sys/types.h>
#include <string.h>
#include <time.h>

#include "configdata.h"
#include "clibrary.h"
#include "libinn.h"

static int s_failed = 0;
static int s_test_no = 0;

#define CHECK(cond, desc)                                          \
    do {                                                           \
        s_test_no++;                                               \
        if (cond) {                                                \
            printf("ok %d - %s\n", s_test_no, desc);               \
        } else {                                                   \
            printf("not ok %d - %s\n", s_test_no, desc);           \
            s_failed++;                                            \
        }                                                          \
    } while (0)

int main(void)
{
    char buf[16];
    TIMEINFO now;
    time_t when;
    const char *ver;

    /* wildmat() returns 1 on match, 0 on plain mismatch. */
    CHECK(wildmat("comp.os.linux", "comp.os.linux") == 1, "wildmat exact match");
    CHECK(wildmat("comp.os.linux", "comp.*") == 1, "wildmat star suffix");
    CHECK(wildmat("comp.os.linux", "*.linux") == 1, "wildmat star prefix");
    CHECK(wildmat("comp.os.linux", "*os*") == 1, "wildmat star both sides");
    CHECK(wildmat("abc", "a?c") == 1, "wildmat question mark");
    CHECK(wildmat("abc", "a[b-d]c") == 1, "wildmat char class hit");
    CHECK(wildmat("abc", "a[xyz]c") == 0, "wildmat char class miss");
    CHECK(wildmat("abc", "abd") == 0, "wildmat literal mismatch");
    CHECK(wildmat("a*b", "a\\*b") == 1, "wildmat escaped star");

    /* Radix32() encodes a 32-bit value in base 32, alphabet 0-9a-v. */
    Radix32(0UL, buf);
    CHECK(strcmp(buf, "0") == 0, "radix32 zero");
    Radix32(1UL, buf);
    CHECK(strcmp(buf, "1") == 0, "radix32 one");
    Radix32(31UL, buf);
    CHECK(strcmp(buf, "v") == 0, "radix32 max digit");
    Radix32(32UL, buf);
    CHECK(strcmp(buf, "10") == 0, "radix32 carry");
    Radix32(100UL, buf);
    CHECK(strcmp(buf, "34") == 0, "radix32 two digits");
    Radix32(1000UL, buf);
    CHECK(strcmp(buf, "v8") == 0, "radix32 mixed digits");

    /* GetTimeInfo()/parsedate() round out the time helpers. */
    CHECK(GetTimeInfo(&now) == 0 && now.time > 0, "gettimeinfo fills TIMEINFO");
    when = parsedate("Thu, 01 Jan 1970 00:00:00 GMT", &now);
    CHECK(when == (time_t)0, "parsedate epoch boundary");
    when = parsedate("Sun, 06 Nov 1994 08:49:37 GMT", &now);
    CHECK(when == (time_t)784111777L, "parsedate RFC 822 vector");
    when = parsedate("not a date @@", &now);
    CHECK(when == (time_t)-1, "parsedate rejects garbage");

    /* INNVersion() identifies the packaged release. */
    ver = INNVersion();
    CHECK(ver != NULL && strncmp(ver, "INN 1.", 6) == 0, "innversion reports INN 1.x");

    printf("# %d tests, %d failures\n", s_test_no, s_failed);
    return s_failed ? 1 : 0;
}
