/* test_package/test.c — run the installed fluent-bit binary to verify the package.
 * This is the L1 official test: it MUST depend on the fluent-bit package,
 * otherwise the R34 destructive negative test (L1e) detects a fake test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    /* Path to the installed fluent-bit binary is passed via the FLUENT_BIT_BIN
     * env var (set by conanfile.py test() — absolute path into the conan
     * package folder). Fall back to PATH lookup only if unset. */
    const char *bin = getenv("FLUENT_BIT_BIN");
    char cmd[512];
    int rc;

    if (!bin || !*bin) {
        bin = "fluent-bit";  /* rely on PATH */
    }

    /* Build a shell command: "<bin>" --version */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version", bin);

    printf("[test] Running: %s\n", cmd);
    rc = system(cmd);
    if (rc != 0) {
        printf("[fail] fluent-bit --version exited %d\n", rc);
        return 1;
    }
    printf("[ok] fluent-bit --version succeeded (exit 0)\n");

    /* Also check --help exits successfully (fluent-bit returns 0 for --help) */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help", bin);
    printf("[test] Running: %s\n", cmd);
    rc = system(cmd);
    if (rc != 0) {
        printf("[fail] fluent-bit --help exited %d\n", rc);
        return 1;
    }
    printf("[ok] fluent-bit --help succeeded (exit 0)\n");
    return 0;
}
