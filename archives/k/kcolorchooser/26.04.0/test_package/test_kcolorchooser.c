/* test_kcolorchooser.c — minimal placeholder for CMake test registration.
 * The real consumer verification runs via test.sh (POSIX sh) from
 * test_package/conanfile.py test(), exercising the shipped
 * bin/kcolorchooser binary. This file compiles to satisfy CMake's
 * enable_testing()/add_test() and prints a sentinel string confirming the
 * build environment is sane.
 */
#include <stdio.h>

int main(void) {
    printf("test_kcolorchooser placeholder — real verification via test.sh\n");
    return 0;
}
