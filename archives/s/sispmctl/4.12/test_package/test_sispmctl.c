/*
 * test_sispmctl.c — L1 consumer test for the sispmctl package.
 *
 * Exercises the real libsispmctl API on the device without requiring a
 * physical GEMBIRD USB power switch (which the CI/real machine does not
 * have). The tested functions are pure library routines that operate on
 * in-memory schedule structures and need no USB hardware:
 *   1. plannif_reset() — initializes the schedule struct (socket/timeStamp
 *      zeroed, every action set to "not scheduled" sentinel -1).
 *   2. pms2_schedule_to_buffer() → pms2_buffer_to_schedule() — round-trip
 *      a schedule through the EG-PMS2 device buffer format and verify the
 *      socket number and start timestamp survive intact.
 *
 * The CLI-driven USB outlet operations themselves are hardware-dependent;
 * the packaged `sispmctl` binary's version/help path is exercised by the
 * test_package wrapper instead.
 */
#include <stdio.h>
#include <string.h>

#include <sispm_ctl.h>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        g_checks++;                                          \
        if (cond) {                                          \
            printf("[ok]   %s\n", msg);                      \
        } else {                                             \
            printf("[fail] %s\n", msg);                      \
            g_failures++;                                    \
        }                                                    \
    } while (0)

int main(void)
{
    const ulong sentinel = (ulong)-1;

    /* --- 1. plannif_reset() --- */
    struct plannif plan;
    memset(&plan, 0xAA, sizeof(plan));      /* corrupt every byte first */
    plannif_reset(&plan);
    CHECK(plan.socket == 0, "plannif_reset() zeroes socket");
    CHECK(plan.timeStamp == 0, "plannif_reset() zeroes timeStamp");
    CHECK(plan.actions[0].switchOn == sentinel &&
          plan.actions[0].timeForNext == sentinel,
          "plannif_reset() seeds actions with the not-scheduled sentinel");
    CHECK(plan.actions[16].switchOn == sentinel &&
          plan.actions[16].timeForNext == sentinel,
          "plannif_reset() initializes the last action entry too");

    /* --- 2. schedule round-trip through the device buffer --- */
    struct plannif sched;
    unsigned char buf[0x28];
    struct plannif back;

    plannif_reset(&sched);
    /* A schedule for socket #1 starting at a distinctive timestamp. */
    sched.socket = 1;
    sched.timeStamp = 0xA0A0A0A0UL;

    int rc = pms2_schedule_to_buffer(&sched, buf);
    CHECK(rc == 0, "pms2_schedule_to_buffer() encodes the schedule (rc=0)");
    CHECK(buf[0] == (3 * sched.socket + 1) & 0xFF,
          "device buffer carries the encoded socket selector byte");

    pms2_buffer_to_schedule(buf, &back);
    CHECK(back.socket == sched.socket,
          "round-trip preserves the socket number");
    CHECK(back.timeStamp == sched.timeStamp,
          "round-trip preserves the start timestamp");

    printf("RESULT total=%d passed=%d failed=%d\n",
           g_checks, g_checks - g_failures, g_failures);
    if (g_failures == 0) {
        printf("ALL libsispmctl API CHECKS PASSED\n");
        return 0;
    }
    return 1;
}
