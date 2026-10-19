#include "c.h"
#include "port/pg_bitutils.h"
#include <stdio.h>
int main(void) {
    const uint32 a[]={0,1,0xffffffffU,0x80000000U,0xaaaaaaaaU,0x01234567U};
    const int ae[]={0,1,32,1,16,12};
    const uint64 b[]={0,1,UINT64_C(0xffffffffffffffff),UINT64_C(0x8000000000000000),UINT64_C(0xaaaaaaaaaaaaaaaa),UINT64_C(0x0123456789abcdef)};
    const int be[]={0,1,64,1,32,32};
    for (unsigned i=0;i<6;i++) {
        if (pg_popcount32(a[i])!=ae[i] || pg_popcount64(b[i])!=be[i]) return 1;
    }
    puts("PORTABLE_POPCOUNT_LITERAL_CHECKS=12 PASS");
    return 0;
}
