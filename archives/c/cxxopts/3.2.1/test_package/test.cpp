#include <cxxopts.hpp>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    cxxopts::Options options("test_package", "Test for cxxopts library");
    options.add_options()
        ("h,help", "Print help")
        ("v,version", "Print version");

    auto result = options.parse(argc, argv);
    if (result.count("help")) {
        std::cout << options.help() << std::endl;
        return 0;
    }
    std::cout << "cxxopts works!" << std::endl;
    return 0;
}
