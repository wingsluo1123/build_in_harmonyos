/* kubetui 1.14.0 consumer test
 * 真实验证 kubetui 二进制：--version 输出非空 + --help 退出码 0
 * aireview: 改用 argv 传 bin_path 避依赖 PATH 巧合 + 避 popen shell 注入风险 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* aireview High+Medium: WIFEXITED/WEXITSTATUS 宏由 POSIX 定义在 sys/wait.h，OHOS musl libc 不保证间接可用 */
#include <sys/wait.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <kubetui binary path>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];

    /* 1. 验证 kubetui --version 输出非空（用 system + 路径传参避 popen shell 注入） */
    char cmd[8192];
    /* aireview P3: shell 注入防御 — 验证路径不含 shell 元字符避注入 */
    if (strpbrk(bin, "\"$;`\\|&")) {
        fprintf(stderr, "FAIL: bin path contains shell metacharacters (injection risk)\n");
        return 3;
    }
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", bin);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run kubetui --version\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    /* aireview P3: pclose 返回值检查 + WEXITSTATUS 解析真实退出码避误报 */
    int pc_ret = pclose(fp);
    if (pc_ret != 0) {
        int real_code = WIFEXITED(pc_ret) ? WEXITSTATUS(pc_ret) : -1;
        /* aireview P3: real_code=-1 时（WIFEXITED false）错误信息精度 — 补 pc_ret raw 帮诊断信号状态 */
        fprintf(stderr, "FAIL: kubetui --version exited with code %d (pclose raw %d%s)\n", real_code, pc_ret,
                 real_code == -1 ? ", WIFEXITED false (killed by signal)" : "");
        return 1;
    }
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: kubetui --version produced no output\n");
        return 1;
    }
    printf("kubetui version: %s", buf);

    /* 2. 验证 kubetui --help 退出码 0（用 argv 传路径避硬编码命令名） */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help > /dev/null 2>&1", bin);
    int ret = system(cmd);
    if (ret != 0) {
        /* P3: system 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        /* aireview P3: real_code=-1 时（WIFEXITED false）错误信息精度 — 补 raw 帮诊断信号状态 */
        fprintf(stderr, "FAIL: kubetui --help exited with code %d (system raw %d%s)\n", real_code, ret,
                 real_code == -1 ? ", WIFEXITED false (killed by signal)" : "");
        return 1;
    }
    printf("kubetui --help OK\n");

    printf("kubetui smoke test PASSED\n");
    return 0;
}
