/* scooter 0.9.1 test_package — 原生场景实际执行 scooter 二进制验证（R34 反空壳）。
 *
 * scooter 是 Rust 应用（cargo build 产出单二进制），无 C 库可链接。
 * 用法：./test_scooter "<scooter_bin_path>" —— 原生场景传入 scooter 二进制路径，
 * 校验 ELF magic 并执行 --version 检查退出码；无参数（交叉编译占位）时仅编译通过。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int is_elf_magic(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    unsigned char magic[4];
    size_t n = fread(magic, 1, 4, f);
    fclose(f);
    return n == 4 && magic[0] == 0x7f && magic[1] == 'E'
           && magic[2] == 'L' && magic[3] == 'F';
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        /* 交叉编译占位：无法在宿主运行 arm64 OHOS 二进制，仅编译通过（L0c 门禁） */
        printf("scooter test_package: compile-only (cross-building placeholder)\n");
        return 0;
    }
    /* 原生场景：先校验 ELF magic（R34 反空壳），再尝试执行 --version 检查退出码 */
    const char *scooter = argv[1];
    /* P1: 修正元字符检测。cmd 中路径被双引号包裹，; | & 在引号内无害；
     * 真正危险的是 " $ ` \（提前结束引号 / 变量展开 / 命令替换 / 转义） */
    if (strchr(scooter, '"') || strchr(scooter, '$') || strchr(scooter, '`') || strchr(scooter, '\\')) {
        fprintf(stderr, "scooter path contains shell metacharacters: %s\n", scooter);
        return 2;
    }
    if (!is_elf_magic(scooter)) {
        fprintf(stderr, "scooter is not a valid ELF file: %s\n", scooter);
        return 3;
    }
    char cmd[1024];
    int n = snprintf(cmd, sizeof(cmd), "\"%s\" --version", scooter);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        fprintf(stderr, "scooter path too long\n");
        return 4;
    }
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "scooter --version failed with exit code %d\n", ret);
        return 1;
    }
    printf("scooter runtime test PASSED (scooter --version exit 0)\n");
    return 0;
}
