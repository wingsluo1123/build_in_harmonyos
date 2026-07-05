#include <stdio.h>
#include "boost/version.hpp"

int main(void) {
    printf("boost version: %d.%d.%d\n",
        BOOST_VERSION / 100000, BOOST_VERSION / 100 % 1000, BOOST_VERSION % 100);
    return 0;
}
