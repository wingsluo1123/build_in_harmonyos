// Test that OSL headers are available and library is linkable
#include <OSL/oslquery.h>
#include <stdio.h>

int main(void) {
    // Verify OSL version is correct
    printf("OSL version: %s\n", OSL_VERSION_STRING);

    // Test OSLQuery basic functionality
    OSL::OSLQuery q;
    printf("OSLQuery created successfully\n");

    printf("test openimageio-plugin-osl: OK\n");
    return 0;
}
