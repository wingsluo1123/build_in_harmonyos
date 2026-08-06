#include <stdio.h>

int main(void) {
    /* This test verifies that the mu package provides a working binary.
       The actual functional test is done by running `mu --version`
       in the conan test_package conanfile.py. */
    printf("test_mu: build successful\n");
    return 0;
}
