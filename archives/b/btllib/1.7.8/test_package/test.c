#include <stdio.h>
#include "btllib/seq.hpp"

int main(void) {
    btllib::Seq seq("test", "ACGTACGT");
    printf("btllib seq: id=%s, seq=%s\n", seq.id.c_str(), seq.seq.c_str());
    return 0;
}
