// Test that boost headers are available and usable (R34: 实质依赖被测包)
// Avoid headers that pull in pthread_setcancelstate (not available on OHOS)
#include <boost/version.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/optional.hpp>
#include <boost/system/error_code.hpp>
#include <iostream>

int main() {
    // Test 1: Check boost version
    std::cout << "Boost version: " << BOOST_LIB_VERSION << std::endl;
    if (BOOST_LIB_VERSION != "1_84") {
        std::cerr << "ERROR: Expected boost version 1_84, got " << BOOST_LIB_VERSION << std::endl;
        return 1;
    }

    // Test 2: Use boost::lexical_cast (header-only)
    std::string s = boost::lexical_cast<std::string>(100);
    if (s != "100") {
        std::cerr << "ERROR: lexical_cast failed" << std::endl;
        return 1;
    }

    // Test 3: Use boost::optional (header-only)
    boost::optional<int> opt = 42;
    if (!opt || *opt != 42) {
        std::cerr << "ERROR: optional value mismatch" << std::endl;
        return 1;
    }

    // Test 4: Use boost::system::error_code (header-only since Boost 1.69)
    boost::system::error_code ec;
    if (ec) {
        std::cerr << "ERROR: default error_code should be false" << std::endl;
        return 1;
    }

    std::cout << "All boost tests passed!" << std::endl;
    return 0;
}
