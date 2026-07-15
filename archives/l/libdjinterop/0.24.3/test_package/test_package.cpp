#include <iostream>
#include "djinterop/djinterop.hpp"

int main(void) {
    auto version = djinterop::version();
    std::cout << "libdjinterop version: " << version << std::endl;
    std::cout << "libdjinterop test OK" << std::endl;
    return 0;
}