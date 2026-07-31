/* kubetui 1.14.0 consumer test
 * 验证 kubetui 二进制已安装并可执行 --help */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("kubetui --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: kubetui --help exited with code %d\n", ret);
        return 1;
    }
    printf("kubetui smoke test PASSED\n");
    return 0;
}
