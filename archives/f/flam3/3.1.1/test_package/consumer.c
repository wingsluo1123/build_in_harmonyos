#include <stdio.h>
#include <string.h>

#include <flam3.h>

int main(void)
{
    const char *version = flam3_version();
    double sample;
    flam3_palette palette;
    if (!version || !strstr(version, "3.1.1"))
        return 1;
    flam3_srandom();
    sample = flam3_random01();
    if (sample < 0.0 || sample >= 1.0)
        return 2;
    if (flam3_get_palette(0, palette, 0.0) != 0 ||
        palette[0].color[0] < 0.0 || palette[0].color[0] > 1.0)
        return 3;
    printf("flam3 %s consumer PASS\n", version);
    return 0;
}
