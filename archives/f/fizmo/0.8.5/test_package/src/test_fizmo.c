#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    /* 允许通过 argv[1] 传入 fizmo-ncursesw 二进制完整路径，默认回退 "fizmo-ncursesw" */
    const char *fizmo = (argc > 1) ? argv[1] : "fizmo-ncursesw";
    char cmd[512];
    char buf[4096];
    size_t n;

    printf("fizmo Test Suite (binary: %s)\n", fizmo);
    printf("================================\n\n");

    /* Test 1: fizmo-ncursesw binary --version prints version info.
     * fizmo-ncursesw 不支持 --help（源码无 --help 参数处理——CI #22792
     * 实测 --help 无输出）——改用 --version 并检查版本号 "0.8.5"
     * （共享库缺失错误消息不含版本号——P2 假阳性规避）。 */
    printf("Test 1: %s --version (output check)\n", fizmo);
    int cmd_len = snprintf(cmd, sizeof(cmd), "%s --version 2>&1", fizmo);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("  ✗ command line too long (need %d, have %zu)\n", cmd_len, sizeof(cmd));
        failed++;
    } else {
        FILE *fp = popen(cmd, "r");
        if (fp == NULL) {
            printf("  ✗ popen failed\n");
            failed++;
        } else {
            n = fread(buf, 1, sizeof(buf) - 1, fp);
            buf[n] = '\0';
            pclose(fp);
            /* 检查版本号 "0.8.5"（PACKAGE_VERSION——fizmo-ncursesw 无
             * --help——共享库缺失错误消息不含版本号——P2 假阳性规避） */
            if (strstr(buf, "0.8.5") != NULL) {
                printf("  ✓ %s --version printed version info\n", fizmo);
                passed++;
            } else {
                printf("  ✗ %s --version output missing version info\n", fizmo);
                failed++;
            }
        }
    }

    printf("\n================================\n");
    printf("Result: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
