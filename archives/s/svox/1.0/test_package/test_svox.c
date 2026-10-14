/* test_svox.c — L1 consumer test for the svox package.
 *
 * Exercises the real libttspico system lifecycle on the device without
 * needing lingware voice data (voice *definitions* are pure in-memory
 * name-table operations, no resource files required):
 *   1. pico_initialize() returns PICO_OK with a non-NULL system handle
 *   2. pico_getNrSystemWarnings() reports PICO_OK and zero warnings
 *   3. pico_getSystemStatusMessage(PICO_OK) returns PICO_OK
 *   4. pico_createVoiceDefinition() a fresh voice returns PICO_OK
 *   5. creating the same voice again fails (negative control: proves the
 *      harness observes real failures instead of blindly passing)
 *   6. pico_releaseVoiceDefinition() returns PICO_OK
 *   7. pico_terminate() returns PICO_OK; the documented init/terminate
 *      cycle repeats (re-initialize + terminate again returns PICO_OK)
 *
 * API contract source: picoapi.h "Basic_Usage" (SVOX Pico 1.0 and later).
 */
#include <stdio.h>
#include <string.h>

#include <picoapi.h>
#include <picodefs.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("[ok]   %s\n", msg);                      \
        } else {                                             \
            printf("[fail] %s\n", msg);                      \
            g_failures++;                                    \
        }                                                    \
    } while (0)

/* Pico manages only the memory handed to it; 4 MiB is well above the
 * minimum for a resourceless system (no engines/voices load lingware). */
static unsigned char g_mem[4 * 1024 * 1024];

int main(void)
{
    pico_System system = NULL;
    pico_Status st;
    pico_Retstring msg;
    pico_Int32 warnings = -1;

    memset(msg, 0, sizeof(msg));

    st = pico_initialize(g_mem, (pico_Uint32)sizeof(g_mem), &system);
    CHECK(st == PICO_OK, "pico_initialize() returns PICO_OK");
    CHECK(system != NULL, "pico_initialize() returns non-NULL system handle");

    st = pico_getNrSystemWarnings(system, &warnings);
    CHECK(st == PICO_OK, "pico_getNrSystemWarnings() returns PICO_OK");
    CHECK(warnings == 0, "fresh system reports zero warnings");

    st = pico_getSystemStatusMessage(system, PICO_OK, msg);
    CHECK(st == PICO_OK, "pico_getSystemStatusMessage(PICO_OK) returns PICO_OK");
    CHECK(msg[sizeof(msg) - 1] == '\0', "status message stays NUL-terminated");

    st = pico_createVoiceDefinition(system, (const pico_Char *)"svoxTest");
    CHECK(st == PICO_OK, "pico_createVoiceDefinition() fresh voice returns PICO_OK");

    st = pico_createVoiceDefinition(system, (const pico_Char *)"svoxTest");
    CHECK(st != PICO_OK, "duplicate voice definition is rejected (negative control)");

    st = pico_releaseVoiceDefinition(system, (const pico_Char *)"svoxTest");
    CHECK(st == PICO_OK, "pico_releaseVoiceDefinition() returns PICO_OK");

    st = pico_terminate(&system);
    CHECK(st == PICO_OK, "pico_terminate() returns PICO_OK");

    /* The documented init/terminate cycle may repeat (useful for apps that
     * need TTS only from time to time). */
    system = NULL;
    st = pico_initialize(g_mem, (pico_Uint32)sizeof(g_mem), &system);
    CHECK(st == PICO_OK && system != NULL, "re-initialize after terminate works");

    st = pico_terminate(&system);
    CHECK(st == PICO_OK, "second terminate returns PICO_OK");

    CHECK(g_failures == 0, "all libttspico API checks passed");
    return g_failures == 0 ? 0 : 1;
}
