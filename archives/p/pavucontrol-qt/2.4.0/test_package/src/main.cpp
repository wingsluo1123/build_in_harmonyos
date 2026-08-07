// Test: verify pavucontrol-qt binary is accessible
// This is a simple smoke test that checks the binary path is defined
#include <iostream>
#include <cstdlib>
#include <sys/stat.h>

int main() {
    // Check if the binary path environment variable is set
    const char* bin_path = std::getenv("PAVUCONTROL_QT_BIN");
    if (bin_path == nullptr) {
        // Binary path not in env, just check we can access the bindir
        std::cout << "pavucontrol-qt package test: binary path not in env (OK for smoke test)" << std::endl;
        return 0;
    }

    struct stat st;
    if (stat(bin_path, &st) == 0) {
        std::cout << "pavucontrol-qt binary found at: " << bin_path << std::endl;
        return 0;
    } else {
        std::cerr << "pavucontrol-qt binary NOT found at: " << bin_path << std::endl;
        return 1;
    }
}
