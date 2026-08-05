#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("apitrace help > /dev/null 2>&1");
    if (ret == 0) {
        ret = system("gltrim --help > /dev/null 2>&1");
    }
    if (ret == 0) {
        printf("test apitrace 14.0: OK (apitrace + gltrim respond)\n");
        return 0;
    } else {
        printf("test apitrace 14.0: FAIL (binary not responding)\n");
        return 1;
    }
}
