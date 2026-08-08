#include "apngasm.h"
#include <iostream>
#include <cstdlib>

int main(void) {
    apngasm::APNGAsm assembler;
    std::string version = assembler.version();
    if (version.empty()) {
        std::cerr << "ERROR: apngasm version() returned empty string" << std::endl;
        return 1;
    }
    std::cout << "apngasm version: " << version << std::endl;
    std::cout << "test apngasm 3.1.10: OK" << std::endl;
    return 0;
}
