#include <stdio.h>
#include <gmp.h>

int main() {
    mpz_t a, b, c;
    mpz_init(a);
    mpz_init(b);
    mpz_init(c);
    
    mpz_set_str(a, "12345678901234567890", 10);
    mpz_set_str(b, "98765432109876543210", 10);
    mpz_add(c, a, b);
    
    printf("GMP test: ");
    mpz_out_str(stdout, 10, c);
    printf("\n");
    
    mpz_clear(a);
    mpz_clear(b);
    mpz_clear(c);
    
    return 0;
}