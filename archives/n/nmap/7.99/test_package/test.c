/* test_nmap.c — L1 test for nmap 7.99
 * R34: test must substantively depend on the tested package.
 * This test executes the nmap binary and verifies its output.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NMAP_BIN NMAP_BINARY_PATH

int main(void) {
    char cmd[512];
    FILE *fp;
    char buf[256];
    int found_version = 0;
    int found_scan = 0;

    /* Test 1: nmap --version */
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", NMAP_BIN);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run nmap --version\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "7.99")) found_version = 1;
    }
    pclose(fp);
    if (!found_version) {
        fprintf(stderr, "FAIL: nmap --version did not output version 7.99\n");
        return 1;
    }
    printf("PASS: nmap --version outputs version 7.99\n");

    /* Test 2: nmap -sL 127.0.0.1 (list scan) */
    snprintf(cmd, sizeof(cmd), "%s -sL 127.0.0.1 2>&1", NMAP_BIN);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run nmap -sL\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "127.0.0.1") || strstr(buf, "localhost")) found_scan = 1;
    }
    pclose(fp);
    if (!found_scan) {
        fprintf(stderr, "FAIL: nmap -sL did not output expected results\n");
        return 1;
    }
    printf("PASS: nmap -sL 127.0.0.1 completed successfully\n");

    printf("All tests passed!\n");
    return 0;
}
