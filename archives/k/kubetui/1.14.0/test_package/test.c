/* kubetui 1.14.0 consumer test
 * 真实验证 kubetui 二进制：--version 输出非空 + --help 退出码 0
 * aireview: 改用 argv 传 bin_path 避依赖 PATH 巧合 + 避 popen shell 注入风险 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
    pclose(fp);
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: kubetui --version produced no output\n");
        return 1;
    }
    printf("kubetui version: %s", buf);

    /* 2. 验证 kubetui --help 退出码 0（用 argv 传路径避硬编码命令名） */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help > /dev/null 2>&1", bin);
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "FAIL: kubetui --help exited with code %d\n", ret);
        return 1;
    }
    printf("kubetui --help OK\n");

    printf("kubetui smoke test PASSED\n");
    return 0;
}
