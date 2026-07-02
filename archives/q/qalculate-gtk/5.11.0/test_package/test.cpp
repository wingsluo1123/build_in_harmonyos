/* test_package/test.cpp — qalculate-gtk 5.11.0
 *
 * Verifies that the qalculate-gtk package correctly brings in libqalculate
 * as a transitive dependency. Includes libqalculate headers and links
 * the library to confirm the dependency chain is intact.
 */
#include <stdio.h>
#include <libqalculate/qalculate.h>

int main(void) {
    /* Verify libqalculate is linked and functional */
    Calculator *calc = new Calculator();
    printf("libqalculate linked successfully via qalculate-gtk package\n");
    delete calc;
    return 0;
}
