/* test_package/test_papi.c — papi 7.2.0 consumer test (OpenHarmony/aarch64).
 *
 * Calls the real libpapi API: library init, version query, component
 * enumeration, event-set create/destroy roundtrip, and shutdown. Every check
 * runs against the packaged library; exit code is 0 only when all pass.
 *
 * The binary prints HMBS_TEST_PACKAGE_RESULT with counts sourced from the
 * same tests_run/tests_failed counters as the Results: summary line.
 */
#include <stdio.h>
#include <string.h>

#include <papi.h>

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    printf("[run] %s\n", #fn); fflush(stdout); \
    tests_run++; \
    if (fn() != 0) { \
        tests_failed++; \
        printf("        [FAIL] %s\n", #fn); fflush(stdout); \
    } else { \
        printf("        [ok] %s\n", #fn); fflush(stdout); \
    } \
} while (0)

/* PAPI_library_init must return the requested interface version. */
static int check_library_init(void) {
    int rc;
    printf("        calling PAPI_library_init...\n"); fflush(stdout);
    rc = PAPI_library_init(PAPI_VER_CURRENT);
    printf("        PAPI_library_init returned %d\n", rc); fflush(stdout);
    if (rc != PAPI_VER_CURRENT) {
        fprintf(stderr, "library_init returned %d, expected %d\n", rc, PAPI_VER_CURRENT);
        return 1;
    }
    return 0;
}

/* PAPI library version must report upstream 7.2.x.
 * Correct API (src/papi.h, src/ctests/version.c): there is no
 * PAPI_version() string accessor; the library version is the int
 * PAPI_VERSION_NUMBER(maj,min,rev,inc) returned by
 * PAPI_get_opt(PAPI_LIB_VERSION, NULL) / PAPI_library_init().
 * A prior revision wrongly assumed `const char *PAPI_version()`,
 * which clang>=19 rejects as int-to-pointer (-Wint-conversion hard
 * error on OHOS). Compare MAJOR/MINOR via the header macros. */
static int check_version_string(void) {
    int v = PAPI_get_opt(PAPI_LIB_VERSION, NULL);
    int major, minor;
    if (v == PAPI_EINVAL || v <= 0) {
        fprintf(stderr, "PAPI_get_opt(LIB_VERSION) failed: %d\n", v);
        return 1;
    }
    major = PAPI_VERSION_MAJOR(v);
    minor = PAPI_VERSION_MINOR(v);
    printf("        PAPI lib version: %d.%d.%d.%d (0x%08x)\n",
           PAPI_VERSION_MAJOR(v), PAPI_VERSION_MINOR(v),
           PAPI_VERSION_REVISION(v), PAPI_VERSION_INCREMENT(v), v);
    fflush(stdout);
    if (major != 7 || minor != 2) {
        fprintf(stderr, "expected 7.2.x, got %d.%d\n", major, minor);
        return 1;
    }
    return 0;
}

/* At least one component (perf_event/sysdetect class) must be active. */
static int check_num_components(void) {
    int n = PAPI_num_components();
    printf("        components: %d\n", n);
    if (n <= 0) {
        fprintf(stderr, "no active PAPI components\n");
        return 1;
    }
    return 0;
}

/* Event-set lifecycle without touching hardware counters. */
static int check_eventset_roundtrip(void) {
    int eventset = PAPI_NULL;
    if (PAPI_create_eventset(&eventset) != PAPI_OK) {
        fprintf(stderr, "PAPI_create_eventset failed\n");
        return 1;
    }
    if (eventset == PAPI_NULL) {
        fprintf(stderr, "eventset handle still PAPI_NULL after create\n");
        return 1;
    }
    if (PAPI_destroy_eventset(&eventset) != PAPI_OK) {
        fprintf(stderr, "PAPI_destroy_eventset failed\n");
        return 1;
    }
    return 0;
}

/* Clean shutdown. Correct API (src/papi.h): `void PAPI_shutdown(void)`.
 * A prior revision wrongly assumed `int PAPI_shutdown()` and compared
 * against PAPI_OK, which clang rejects as void-vs-int. There is no
 * return to check; reaching the call after the earlier checks is the
 * test (upstream ctests call it the same way). */
static int check_shutdown(void) {
    PAPI_shutdown();
    return 0;
}

int main(void) {
    printf("=== papi 7.2.0 test_package (OpenHarmony/aarch64) ===\n"); fflush(stdout);

    RUN(check_library_init);
    RUN(check_version_string);
    RUN(check_num_components);
    RUN(check_eventset_roundtrip);
    RUN(check_shutdown);

    printf("=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);

    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_papi\",\"discovered\":5,\"passedCount\":%d}\n",
           tests_failed == 0 ? "true" : "false", tests_run - tests_failed);

    if (tests_failed == 0) {
        printf("All papi API checks PASSED.\n");
        return 0;
    }
    printf("%d check(s) FAILED.\n", tests_failed);
    return 1;
}
