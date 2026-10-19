#include <sympol/qarray.h>
#include <cstdio>

int main() {
    sympol::QArray value(3);
    if (value.size() != 3) return 1;
    mpq_set_si(value[0], 1, 2);
    mpq_set_si(value[1], 2, 3);
    mpq_set_si(value[2], 3, 4);
    mpz_t lcm;
    mpz_init(lcm);
    value.denominatorLCM(lcm);
    bool valid = mpz_cmp_ui(lcm, 12) == 0;
    mpz_clear(lcm);
    if (!valid) return 2;
    sympol::QArray copied(value);
    if (copied.size() != 3 || mpq_cmp(copied[1], value[1]) != 0) return 3;
    copied += value;
    if (mpq_cmp_ui(copied[0], 1, 1) != 0) return 4;
    std::puts("SYMPOL_CONSUMER_PASS 4 checks: size denominator-lcm copy addition");
    return 0;
}
