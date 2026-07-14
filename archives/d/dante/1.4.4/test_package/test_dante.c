/* test_dante.c — verify libsocks API is callable */
#include <socks.h>

/* Wrapper to call dante's SOCKSinit API with a lowercase name */
static int socks_init_test(void) {
    SOCKSinit("test_dante");
    return 0;
}

int main(void) {
    /* Initialize dante SOCKS library to verify linkage */
    socks_init_test();
    return 0;
}
