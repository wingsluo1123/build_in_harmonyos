/* test_package/test.c — rpki-client 9.6
 *
 * R34: Test must exercise the package's binary, not just print a string.
 * rpki-client is a command-line tool (not a library), so we invoke
 * rpki-client -V via popen() and verify the output contains "9.6".
 *
 * The rpki-client binary path is provided via the RPKI_CLIENT_PATH
 * environment variable (set by conanfile.py test() method).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "9.6"

int main(void) {
    FILE *fp;
    char buf[512];
    int found = 0;
    char cmd[512];

    /* Get rpki-client binary path from environment */
    const char *rpki_path = getenv("RPKI_CLIENT_PATH");
    if (rpki_path == NULL || rpki_path[0] == '\0') {
        rpki_path = "rpki-client";
    }

    /* Run rpki-client -V and capture output */
    snprintf(cmd, sizeof(cmd), "%s -V 2>&1", rpki_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_VERSION) != NULL) {
            found = 1;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: rpki-client exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: rpki-client -V output does not contain '%s'\n", EXPECTED_VERSION);
        return 1;
    }

    printf("test rpki-client 9.6: OK (version verified)\n");
    return 0;
}
