#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* This test binary is built by CMake to verify the build environment.
     * The actual functional test runs irssi --version in conanfile.py test().
     */
    printf("irssi test package: build OK\n");
    return 0;
}
