#include <stdio.h>
#define NOLIBCNAMES
#include "iraf_setjmp.h"

static int check(XINT requested)
{
    jmp_buf buffer;
    volatile XINT status = -1;
    ZSVJMP(buffer, &status);
    if (status == 0) {
        ZDOJMP(buffer, &requested);
        return 1;
    }
    return status == (requested ? requested : 1) ? 0 : 1;
}

static int check_macro(XINT requested)
{
    jmp_buf buffer;
    XINT result = setjmp(buffer);
    if (result == 0) {
        longjmp(buffer, requested);
        return 1;
    }
    return result == (requested ? requested : 1) ? 0 : 1;
}

int main(void)
{
    if (check(42) || check(0) || check(-7) ||
        check_macro(42) || check_macro(0) || check_macro(-7))
        return 1;
    puts("IRAF_CONTEXT=6/6");
    return 0;
}
