/* git-who 1.3 consumer test
 * 验证 git-who 二进制已安装并可执行 --help */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* git-who 已通过 conanrun 环境暴露在 PATH 中 */
    int ret = system("git-who --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: git-who --help exited with code %d\n", ret);
        return 1;
    }
    printf("git-who smoke test PASSED\n");
    return 0;
}
