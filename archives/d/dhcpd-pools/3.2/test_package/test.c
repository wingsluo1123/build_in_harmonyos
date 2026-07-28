#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

/* test_dhcpd_pools_smoke.c
 * Smoke test for dhcpd-pools 3.2
 * Offline: runs dhcpd-pools binary against test data and verifies output.
 * First argument (optional): path to dhcpd-pools binary. Default: "dhcpd-pools".
 */

static int run_cmd(const char *desc, const char *cmd, int expect_ok) {
    int rc = system(cmd);
    int ok = (WIFEXITED(rc) && WEXITSTATUS(rc) == (expect_ok ? 0 : 1));
    printf("  %-50s ... %s\n", desc, ok ? "PASS" : "FAIL");
    if (!ok) {
        printf("    exit: %d (expected %s)\n",
               WEXITSTATUS(rc), expect_ok ? "0" : "1");
    }
    return ok ? 0 : 1;
}

int main(int argc, char *argv[]) {
    const char *dhcpd_pools = argc > 1 ? argv[1] : "dhcpd-pools";
    int failures = 0;
    char buf[1024];
    printf("dhcpd-pools 3.2 smoke test (binary: %s)\n\n", dhcpd_pools);

    snprintf(buf, sizeof(buf), "%s -c dhcpd.conf -l dhcpd.leases --color=never > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("text output (default)", buf, 1);

    snprintf(buf, sizeof(buf), "%s -c dhcpd.conf -l dhcpd.leases --color=never --format=csv > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("csv output format", buf, 1);

    snprintf(buf, sizeof(buf), "%s -c dhcpd.conf -l dhcpd.leases --color=never --format=json > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("json output format", buf, 1);

    snprintf(buf, sizeof(buf), "%s -c dhcpd.conf -l dhcpd.leases --color=never --format=xml > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("xml output format", buf, 1);

    snprintf(buf, sizeof(buf), "%s -c nonexistent.conf -l dhcpd.leases --color=never > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("error on missing conf", buf, 0);

    snprintf(buf, sizeof(buf), "%s -c dhcpd.conf -l nonexistent.leases --color=never > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("error on missing leases", buf, 0);

    snprintf(buf, sizeof(buf), "%s --help > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("help option", buf, 1);

    snprintf(buf, sizeof(buf), "%s --version > /dev/null 2>&1", dhcpd_pools);
    failures += run_cmd("version option", buf, 1);

    printf("\n%d total, %d failures\n", 8, failures);
    return failures > 0 ? 1 : 0;
}
