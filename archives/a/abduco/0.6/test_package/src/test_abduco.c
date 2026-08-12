// R34: 实质调用 abduco 二进制 — --version 输出验证
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    // popen 捕获 abduco --version 输出并检查非空（验证二进制可执行且
    // 输出版本信息，非空壳）。argv[1] 传 abduco 二进制完整路径
    // （usr/bin/abduco——make install PREFIX=/usr——不依赖 PATH）
    const char *ab = (argc > 1) ? argv[1] : "abduco";
    char cmd[512];
    int cmd_len = snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", ab);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("abduco --version: FAILED (command truncated)\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("abduco --version: FAILED (popen failed)\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);
    if (n > 0) {
        printf("abduco --version: OK (output %zu bytes)\n", n);
        return 0;
    }
    printf("abduco --version: FAILED (no output)\n");
    return 1;
}
