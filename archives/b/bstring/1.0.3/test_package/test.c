#include <stdio.h>
#include "bstrlib.h"

int main(void) {
    bstring s = bfromcstr("hello world");
    printf("bstring: '%s', len=%d\n", s->data, s->slen);
    bdestroy(s);
    return 0;
}
