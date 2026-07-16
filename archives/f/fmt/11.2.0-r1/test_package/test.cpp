// test_package/test.cpp — R34 compliant test for fmt/11.2.0-r1
// Substantially depends on the tested package by calling fmt API.
#include <fmt/format.h>
#include <fmt/ostream.h>

#include <cassert>
#include <string>

int main() {
    // Test 1: Basic format
    std::string s = fmt::format("Hello, {}!", "world");
    assert(s == "Hello, world!");

    // Test 2: Numeric formatting
    std::string num = fmt::format("The answer is {}", 42);
    assert(num == "The answer is 42");

    // Test 3: Multiple arguments
    std::string multi = fmt::format("{0} + {1} = {2}", 2, 3, 5);
    assert(multi == "2 + 3 = 5");

    // Test 4: fmt::print (to stdout)
    fmt::print("fmt test passed: {} formatted strings\n", 3);

    // Test 5: fmt::to_string
    std::string str = fmt::to_string(3.14);
    assert(!str.empty());

    return 0;
}
