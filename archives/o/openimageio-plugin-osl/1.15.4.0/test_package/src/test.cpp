// Test that OSL headers and libraries are usable.
// This test includes OSL's oslquery header and creates an OSLQuery object,
// which exercises the OSL API and links against OSL libraries.
#include <OSL/oslquery.h>
#include <iostream>

int main() {
    // Create an OSLQuery object to verify the library is linked
    OSL::OSLQuery q;
    std::cout << "OSL test: OSLQuery created successfully" << std::endl;
    return 0;
}
