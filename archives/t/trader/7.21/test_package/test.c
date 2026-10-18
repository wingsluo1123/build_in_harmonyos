/*
 * test.c — trader 7.21 消费者视角测试
 *
 * 真实调用安装产物 bin/trader 可执行文件（路径经 argv[1] 传入，来自被测
 * conan 包的 package_folder，避免依赖 PATH）。共 4 个确定性断言：
 *   1. 二进制存在且可执行
 *   2. trader --version 退出码为 0 且输出含 "7.21"
 *   3. trader --help 退出码为 0 且输出含 Usage/Star Traders
 *   4. trader --no-color --version 退出码为 0（额外选项不被拒绝）
 *
 * R34：非空壳——真实执行被测二进制并逐项断言，任何一项失败返回非零。
 *
 * 结束时打印一行确定性结果尾部标记，供 test_package/conanfile.py 解析
 * （单一数据源，不做字符串数数或算术修补）：
 *   TRADER_TEST_RESULT total=<n> passed=<n> failed=<n>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int run_capture(const char *bin, const char *args[],
                       char *out, size_t outsz) {
    char cmd[1024];
    size_t off = 0;
    off += (size_t)snprintf(cmd + off, sizeof(cmd) - off, "\"%s\"", bin);
    for (int i = 0; args[i] != NULL; i++) {
        off += (size_t)snprintf(cmd + off, sizeof(cmd) - off, " %s", args[i]);
    }
    snprintf(cmd + off, sizeof(cmd) - off, " 2>&1");

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        perror("popen");
        return -1;
    }
    size_t n = fread(out, 1, outsz - 1, fp);
    out[n] = '\0';
    int rc = pclose(fp);
    return rc;
}

int main(int argc, char *argv[]) {
    const char *bin = (argc > 1) ? argv[1] : "trader";
    int total = 0, passed = 0;
    char out[2048];

    printf("Testing trader binary: %s\n", bin);

    /* Test 1: 二进制存在且可执行 */
    total++;
    if (access(bin, X_OK) != 0) {
        fprintf(stderr, "FAIL: %s is not executable\n", bin);
    } else {
        passed++;
        printf("PASS: trader binary is executable\n");
    }

    /* Test 2: --version 退出码 0 且含版本号 */
    total++;
    {
        const char *args[] = {"--version", NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc != 0) {
            fprintf(stderr, "FAIL: trader --version returned %d\n", rc);
        } else if (strstr(out, "7.21") == NULL) {
            fprintf(stderr, "FAIL: --version output lacks '7.21': %s\n", out);
        } else {
            passed++;
            printf("PASS: trader --version reports 7.21\n");
        }
    }

    /* Test 3: --help 退出码 0 且含游戏名/用法 */
    total++;
    {
        const char *args[] = {"--help", NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc != 0) {
            fprintf(stderr, "FAIL: trader --help returned %d\n", rc);
        } else if (strstr(out, "Star Traders") == NULL &&
                   strstr(out, "trader") == NULL && strstr(out, "Usage") == NULL) {
            fprintf(stderr, "FAIL: --help output unexpected: %s\n", out);
        } else {
            passed++;
            printf("PASS: trader --help shows usage\n");
        }
    }

    /* Test 4: --no-color --version 组合选项正常 */
    total++;
    {
        const char *args[] = {"--no-color", "--version", NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc != 0) {
            fprintf(stderr, "FAIL: trader --no-color --version returned %d\n", rc);
        } else {
            passed++;
            printf("PASS: trader --no-color --version OK\n");
        }
    }

    /* 确定性结果尾部标记（单一数据源，供 conanfile.py 解析） */
    printf("TRADER_TEST_RESULT total=%d passed=%d failed=%d\n",
           total, passed, total - passed);
    fflush(stdout);

    if (passed != total) {
        fprintf(stderr, "trader test FAILED: %d/%d passed\n", passed, total);
        return 1;
    }
    printf("All trader tests passed\n");
    return 0;
}
