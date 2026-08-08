/* test_package/src/test.c — verifies rom-tools CLI binaries work */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int ret;
    char buf[256];
    FILE *fp;

    /* Run chdman and capture output */
    fp = popen("chdman info 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot run chdman\n");
        return 1;
    }
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        pclose(fp);
        fprintf(stderr, "FAIL: chdman produced no output\n");
        return 1;
    }
    pclose(fp);
    if (strstr(buf, "chdman") == NULL) {
        fprintf(stderr, "FAIL: chdman output unexpected: %s\n", buf);
        return 1;
    }
    printf("PASS: chdman runs and prints version info\n");

    /* Run romcmp and capture output */
    fp = popen("romcmp 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot run romcmp\n");
        return 1;
    }
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        pclose(fp);
        fprintf(stderr, "FAIL: romcmp produced no output\n");
        return 1;
    }
    pclose(fp);
    if (strstr(buf, "romcmp") == NULL) {
        fprintf(stderr, "FAIL: romcmp output unexpected: %s\n", buf);
        return 1;
    }
    printf("PASS: romcmp runs and prints usage\n");

    printf("All tests passed\n");
    return 0;
}
