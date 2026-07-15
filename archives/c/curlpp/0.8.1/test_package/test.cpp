// test_package/test.cpp — curlpp consumer smoke test
// Verifies curlpp library is correctly built and linked.
// Calls curlpp::initialize/terminate lifecycle API (R34: real API call).

#include <curlpp/cURLpp.hpp>
#include <curlpp/Easy.hpp>
#include <curlpp/Options.hpp>

#include <iostream>
#include <cstdlib>

int main() {
    try {
        curlpp::initialize(CURL_GLOBAL_ALL);
        {
            curlpp::Easy request;
            request.setOpt<curlpp::options::Url>("http://example.com");
        }
        curlpp::terminate();
        std::cout << "curlpp lifecycle test passed" << std::endl;
        return 0;
    } catch (curlpp::RuntimeError &e) {
        std::cerr << "curlpp runtime error: " << e.what() << std::endl;
        return 1;
    } catch (curlpp::LogicError &e) {
        std::cerr << "curlpp logic error: " << e.what() << std::endl;
        return 1;
    }
}
