// Test source for pamixer test_package
// Verifies that pamixer binary is installed and responds to --version
#include <cstdlib>
#include <iostream>
#include <string>

int main() {
    // Execute pamixer --version to verify the binary is installed and functional
    int ret = system("pamixer --version");
    if (ret != 0) {
        std::cerr << "pamixer --version failed" << std::endl;
        return 1;
    }
    std::cout << "pamixer binary test passed" << std::endl;
    return 0;
}
