/* klystrack 0.20171212 consumer test
 * �实验证 klystrack 二进制：--version 输出非空 + --help 退出码 0 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* 1. 验证 klystrack --version 输出非空 */
    FILE *fp = popen("klystrack --version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run klystrack --version\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    /* P2: pclose 返回值检查（aireview: 忽略致二进制运行失败时仍报通过） */
    int pc_ret = pclose(fp);
    if (pc_ret != 0) {
        fprintf(stderr, "FAIL: klystrack --version exited with code %d\n", pc_ret);
        return 1;
    }
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: klystrack --version produced no output\n");
        return 1;
    }
    printf("klystrack version: %s", buf);

    /* 2. 验证 klystrack --help 退出码 0 */
    int ret = system("klystrack --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: klystrack --help exited with code %d\n", ret);
        return 1;
    }
    printf("klystrack --help OK\n");

    printf("klystrack smoke test PASSED\n");
    return 0;
}
