/* git-who 1.3 consumer test
 * 验证 git-who 二进制已安装并可执行 --help */
#include <stdio.h>
#include <stdlib.h>
/* aireview High: WIFEXITED/WEXITSTATUS 宏由 POSIX 定义在 sys/wait.h，OHOS musl libc 不保证间接可用 */
#include <sys/wait.h>

int main(void) {
    /* git-who 已通过 conanrun 环境暴露在 PATH 中 */
    int ret = system("git-who --help > /dev/null 2>&1");
    if (ret != 0) {
        /* P3: system 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        fprintf(stderr, "FAIL: git-who --help exited with code %d (system raw %d)\n", real_code, ret);
        return 1;
    }
    printf("git-who smoke test PASSED\n");
    return 0;
}
