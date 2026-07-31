/* kubetui 1.14.0 consumer test
 * 真实验证 kubetui 二进制：--version 输出非空 + --help 退出码 0 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* 1. 验证 kubetui --version 输出非空 */
    FILE *fp = popen("kubetui --version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run kubetui --version\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    pclose(fp);
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: kubetui --version produced no output\n");
        return 1;
    }
    printf("kubetui version: %s", buf);

    /* 2. 验证 kubetui --help 退出码 0 */
    int ret = system("kubetui --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: kubetui --help exited with code %d\n", ret);
        return 1;
    }
    printf("kubetui --help OK\n");

    printf("kubetui smoke test PASSED\n");
    return 0;
}
