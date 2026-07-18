#include <stdlib.h>
#include <stdio.h>

int main() {
    int ret = system("lv --help > /dev/null 2>&1");
    if (ret != 0) {
        printf("FAIL: lv --help failed with exit code %d\n", ret);
        return 1;
    }
    printf("test lv 4.51-10.1: OK (lv --help passed)\n");
    return 0;
}
