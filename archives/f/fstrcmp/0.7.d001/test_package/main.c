#include <stdio.h>
#include <fstrcmp.h>

int main(void)
{
    double same = fstrcmp("kodi", "kodi");
    double close = fstrcmp("kodi", "kod1");
    printf("fstrcmp(kodi,kodi)=%g fstrcmp(kodi,kod1)=%g\n", same, close);
    if (!(same > 0.99))
        return 1;
    if (!(close >= 0.0 && close <= 1.0))
        return 2;
    printf("fstrcmp smoke passed\n");
    return 0;
}
