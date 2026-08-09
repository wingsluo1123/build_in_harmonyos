#include <cstdio>

/* Simple smoke test: verifies the test_package builds and links.
 * The actual keyfinder-cli binary test is run by conanfile.py test(). */
int main() {
    printf("test_keyfinder_cli: build and link OK\n");
    return 0;
}
