/* test_cleo.c — cleo 消费者测试
 * 验证 cleo Perl CLI 安装：
 *   1. bin/cleo 脚本存在且可执行
 *   2. perl -c bin/cleo 语法检查通过（间接验证 Perl 模块依赖链）
 * 编译：clang test_cleo.c -o test_cleo
 * 运行：./test_cleo <cleo_bin> <perl>
 * 退出码：0=通过，非 0=失败
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <cleo_bin> <perl>\n", argv[0]);
        return 2;
    }
    const char *cleo = argv[1];
    const char *perl = argv[2];
    if (access(cleo, X_OK) != 0) {
        fprintf(stderr, "FAIL: cleo binary not found or not executable: %s\n", cleo);
        return 3;
    }
    /* perl -c cleo：语法检查（验证 shebang Perl + 模块依赖链可加载） */
    char cmd[8192];
    snprintf(cmd, sizeof(cmd), "\"%s\" -c \"%s\" 2>&1", perl, cleo);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run perl -c\n");
        return 4;
    }
    char buf[4096];
    int ok = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "syntax OK")) {
            ok = 1;
            break;
        }
    }
    pclose(fp);
    if (!ok) {
        fprintf(stderr, "FAIL: perl -c cleo did not report syntax OK\n");
        return 5;
    }
    printf("cleo: binary OK, perl syntax check OK\n");
    return 0;
}
