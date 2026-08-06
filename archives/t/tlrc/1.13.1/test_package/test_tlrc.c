/* tlrc 1.13.1 test_package — 原生场景实际执行 tldr 二进制验证（R34 反空壳）。
 *
 * tlrc 是 Rust 应用（cargo build 产出单二进制），无 C 库可链接。
 * 用法：./test_tlrc "<tldr_bin_path>" —— 原生场景传入 tldr 二进制路径，
 * 执行 `<tldr> --version` 并检查退出码；无参数（交叉编译占位）时仅编译通过。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        /* 交叉编译占位：无法在宿主运行 arm64 OHOS 二进制，仅编译通过（L0c 门禁） */
        printf("tlrc test_package: compile-only (cross-building placeholder)\n");
        return 0;
    }
    /* 原生场景：实际执行 tldr --version 并检查退出码（R34 反空壳） */
    const char *tldr = argv[1];
    if (strchr(tldr, '"') || strchr(tldr, ';') || strchr(tldr, '|') || strchr(tldr, '&')) {
        fprintf(stderr, "tldr path contains shell metacharacters: %s\n", tldr);
        return 2;
    }
    char cmd[1024];
    int n = snprintf(cmd, sizeof(cmd), "\"%s\" --version", tldr);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        fprintf(stderr, "tldr path too long\n");
        return 3;
    }
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "tldr --version failed with exit code %d\n", ret);
        return 1;
    }
    printf("tlrc runtime test PASSED (tldr --version exit 0)\n");
    return 0;
}
