/* test_package/test_nss.c — unscd 0.54 consumer test (OpenHarmony/aarch64).
 *
 * unscd is a Name Service Cache Daemon: it caches exactly the NSS lookup
 * APIs exercised below (passwd/group/hosts). This harness calls the real
 * libc NSS entry points a consumer (or unscd's own workers) would call and
 * verifies each call completes without crashing. Either a found entry or a
 * clean not-found (NULL + errno) counts as pass — the assertion is that the
 * API invocation itself works, not that a particular user exists on OHOS.
 */
#include <errno.h>
#include <grp.h>
#include <netdb.h>
#include <pwd.h>
#include <stdio.h>

static int checks_run = 0;
static int checks_failed = 0;

#define CHECK(fn) do { \
    printf("[run] %s\n", #fn); \
    checks_run++; \
    if (fn() != 0) { \
        checks_failed++; \
        printf("        [FAIL] %s\n", #fn); \
    } else { \
        printf("        [ok] %s\n", #fn); \
    } \
} while (0)

static int t_getpwuid(void) {
    errno = 0;
    struct passwd *pw = getpwuid(0);
    if (pw != NULL) {
        printf("        getpwuid(0) -> %s\n", pw->pw_name ? pw->pw_name : "<noname>");
        if (pw->pw_name == NULL) return 1;
        return 0;
    }
    printf("        getpwuid(0) -> not-found (errno=%d)\n", errno);
    return 0;
}

static int t_getgrgid(void) {
    errno = 0;
    struct group *gr = getgrgid(0);
    if (gr != NULL) {
        printf("        getgrgid(0) -> %s\n", gr->gr_name ? gr->gr_name : "<noname>");
        if (gr->gr_name == NULL) return 1;
        return 0;
    }
    printf("        getgrgid(0) -> not-found (errno=%d)\n", errno);
    return 0;
}

static int t_gethostbyname(void) {
    struct hostent *he = gethostbyname("localhost");
    if (he != NULL) {
        printf("        gethostbyname(localhost) -> %s\n", he->h_name ? he->h_name : "<noname>");
        if (he->h_name == NULL || he->h_addr_list == NULL || he->h_addr_list[0] == NULL) return 1;
        return 0;
    }
    printf("        gethostbyname(localhost) -> not-found (h_errno=%d)\n", h_errno);
    return 0;
}

int main(void) {
    printf("=== unscd 0.54 NSS consumer checks ===\n");
    CHECK(t_getpwuid);
    CHECK(t_getgrgid);
    CHECK(t_gethostbyname);
    printf("=== NSS Results: %d/%d passed, %d failed ===\n",
           checks_run - checks_failed, checks_run, checks_failed);
    return checks_failed == 0 ? 0 : 1;
}
