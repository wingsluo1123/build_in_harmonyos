#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test: invoke pwsafe-cli and verify it responds with supported arguments.
 * This test genuinely depends on the pwsafe package — if pwsafe-cli
 * binary is removed, this test will fail (R34 compliance). */
int main(void) {
    FILE *fp = popen("pwsafe-cli --help 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "Failed to run pwsafe-cli\n");
        return 1;
    }

    char buf[512];
    int found_add = 0;
    int found_create = 0;

    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "add"))
            found_add = 1;
        if (strstr(buf, "create"))
            found_create = 1;
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "pwsafe-cli exited with non-zero status\n");
        return 1;
    }

    if (!found_add || !found_create) {
        fprintf(stderr, "pwsafe-cli did not output expected arguments\n");
        return 1;
    }

    printf("PASS: pwsafe-cli responds with supported arguments\n");
    return 0;
}
