/* test_package/test.c — qtshadertools 6.11.1
 * Verifies that the qtshadertools conan package can be found and configured.
 * The actual library link test is handled by find_package() in CMakeLists.txt.
 */
#include <stdio.h>

int main(void) {
    printf("qtshadertools 6.11.1: package found and configured OK\n");
    return 0;
}
