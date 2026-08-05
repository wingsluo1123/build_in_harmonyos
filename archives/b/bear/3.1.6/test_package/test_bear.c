/* test_bear.c — Smoke test for bear package
 * Verifies the bear binary is installed and functional.
 * The actual binary test is run via conanfile.py test() method
 * which executes `bear --version`.
 */
#include <stdlib.h>

int main(void) {
    /* If the package is correctly installed, this test compiles
     * and the conanfile.py test() runs bear --version separately. */
    return EXIT_SUCCESS;
}
