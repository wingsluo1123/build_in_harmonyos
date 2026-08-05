#include <iostream>
#include <string>

int main() {
    const std::string message = "gcc@12 C++ smoke ok";
    if (message.find("C++") == std::string::npos) {
        return 1;
    }
    std::cout << message << '\n';
    return 0;
}
