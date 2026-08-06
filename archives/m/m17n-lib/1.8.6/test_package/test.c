#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* m17n-lib full API - m17n.h includes m17n-core.h and declares m17n_init() */
#include <m17n.h>

int main(void) {
    /* Initialize m17n library (core symbols are initialized here) */
    m17n_init();

    /* Test symbol creation - core m17n API */
    MSymbol sym = msymbol("test_symbol");
    if (sym == Mnil) {
        fprintf(stderr, "FAIL: msymbol returned NULL or Mnil\n");
        return 1;
    }

    /* Test symbol name retrieval */
    char *name = msymbol_name(sym);
    if (name == NULL || strcmp(name, "test_symbol") != 0) {
        fprintf(stderr, "FAIL: msymbol_name returned '%s'\n", name ? name : "NULL");
        return 1;
    }

    printf("test m17n-lib 1.8.6: OK (symbol='%s')\n", name);
    m17n_fini();
    return 0;
}
