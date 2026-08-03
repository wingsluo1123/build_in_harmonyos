/* git-who 1.3 consumer test
 * 验证 git-who 二进制已安装并可执行 --help
 * aireview: 改用 argv 传 bin_path 避依赖 PATH 巧合 + 避 system shell 注入风险 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* aireview High: WIFEXITED/WEXITSTATUS 宏由 POSIX 定义在 sys/wait.h，OHOS musl libc 不保证间接可用 */
#include <sys/wait.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <git-who binary path>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    /* aireview P3: shell 注入防御 — 验证路径不含 shell 元字符避注入 */
    if (strpbrk(bin, "\"$;`\\|&")) {
        fprintf(stderr, "FAIL: bin path contains shell metacharacters (injection risk)\n");
        return 3;
    }
    /* git-who 已通过 conanrun 环境暴露在 PATH 中，但用 argv 传路径避依赖 PATH 巧合 */
    char cmd[8192];
    int sn_ret = snprintf(cmd, sizeof(cmd), "\"%s\" --help > /dev/null 2>&1", bin);
    /* aireview P3: snprintf 截断未检查 — 返值 >=size 表示截断，bin 路径过长致命令截断注入风险 */
    if (sn_ret < 0 || (size_t)sn_ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command buffer truncated (snprintf ret %d, buf %zu)\n", sn_ret, sizeof(cmd));
        return 4;
    }
    int ret = system(cmd);
    if (ret != 0) {
        /* P3: system 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        /* aireview P3: real_code=-1 时（WIFEXITED false）错误信息精度 — 补 raw 帮诊断信号状态 */
        fprintf(stderr, "FAIL: git-who --help exited with code %d (system raw %d%s)\n", real_code, ret,
                 real_code == -1 ? ", WIFEXITED false (killed by signal)" : "");
        return 1;
    }
    printf("git-who smoke test PASSED\n");
    return 0;
}
