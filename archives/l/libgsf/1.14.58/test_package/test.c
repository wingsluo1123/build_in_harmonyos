#include <stdio.h>
#include <gsf/gsf.h>

int main(void) {
    gsf_init();
    printf("libgsf 1.14.58: gsf_init() OK\n");
    gsf_shutdown();
    printf("test libgsf 1.14.58: PASS\n");
    return 0;
}
