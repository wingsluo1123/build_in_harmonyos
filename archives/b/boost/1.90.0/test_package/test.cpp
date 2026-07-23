#include <stdio.h>
#include <stdlib.h>
#include <string>

/* Verify that key Boost headers are includable */
#include <boost/version.hpp>
#include <boost/config.hpp>
#include <boost/smart_ptr.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/optional.hpp>
#include <boost/variant.hpp>
#include <boost/tuple/tuple.hpp>
#include <boost/function.hpp>
#include <boost/bind/bind.hpp>

/* Boost.Regex — requires the compiled library */
#include <boost/regex.hpp>

int main(void) {
    printf("Boost version: %d\n", BOOST_VERSION);
    printf("Boost header-only test: PASSED\n");

    /* Simple boost::optional test */
    boost::optional<int> opt_val = 42;
    if (opt_val) {
        printf("boost::optional test: PASSED (value=%d)\n", *opt_val);
    }

    /* Simple boost::lexical_cast test */
    try {
        int val = boost::lexical_cast<int>("123");
        printf("boost::lexical_cast test: PASSED (value=%d)\n", val);
    } catch (...) {
        printf("boost::lexical_cast test: FAILED\n");
        return 1;
    }

    /* Boost.Regex — requires actual library linking */
    {
        std::string line = "Subject: Hello World";
        boost::regex pat("Subject: (.*)");
        boost::smatch matches;
        if (boost::regex_search(line, matches, pat)) {
            printf("boost::regex_search test: PASSED (matched=%s)\n",
                   matches[1].str().c_str());
        } else {
            printf("boost::regex_search test: FAILED (no match)\n");
            return 1;
        }
    }

    return 0;
}
