/* test_package/test_debianutils.c — smoke test for debianutils executables.
 * Invokes run-parts and ischroot binaries via system() to verify they are
 * functional. The actual conan test() runs test.sh which calls these same
 * binaries in the conanrun environment.
 */
#include <stdlib.h>
#include <stdio.h>

int main(void) {
    /* R34: Substantive test — calls the tested package's binaries. */
    int rc = system("run-parts --version");
    if (rc != 0) {
        fprintf(stderr, "run-parts --version failed (rc=%d)\n", rc);
        return 1;
    }

    rc = system("ischroot --version");
    if (rc != 0) {
        fprintf(stderr, "ischroot --version failed (rc=%d)\n", rc);
        return 1;
    }

    printf("All debianutils smoke tests passed.\n");
    return 0;
}
