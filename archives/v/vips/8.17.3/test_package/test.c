#include <vips/vips.h>
#include <stdio.h>

int main(void) {
    if (vips_init(NULL) != 0) {
        fprintf(stderr, "vips_init failed\n");
        return 1;
    }
    printf("vips version: %s\n", vips_version_string());
    vips_shutdown();
    return 0;
}
