#include <stdio.h>
#include <string.h>
#include <liquid/liquid.h>

int main(void) {
    const char *version = liquid_libversion();
    int version_num = liquid_libversion_number();

    printf("liquid-dsp version: %s (0x%06x)\n", version, version_num);

    // Verify version matches expected (1.8.0)
    if (LIQUID_VERSION_NUMBER != version_num) {
        fprintf(stderr, "ERROR: Header version (0x%06x) != library version (0x%06x)\n",
                LIQUID_VERSION_NUMBER, version_num);
        return 1;
    }

    printf("liquid-dsp v1.8.0: OK\n");
    return 0;
}
