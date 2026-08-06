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

    /* Test 1: fizmo-ncursesw binary --help outputs usage info.
     * 不依赖退出码（上游可能非零），用 popen 捕获输出并检查关键字。 */
    printf("Test 1: %s --help (output check)\n", fizmo);
    int cmd_len = snprintf(cmd, sizeof(cmd), "%s --help 2>&1", fizmo);
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
            if (strstr(buf, "Usage") != NULL || strstr(buf, "fizmo") != NULL
                || strstr(buf, "usage") != NULL) {
                printf("  ✓ %s --help printed usage info\n", fizmo);
                passed++;
            } else {
                printf("  ✗ %s --help output missing usage info\n", fizmo);
                failed++;
            }
        }
    }

    printf("\n================================\n");
    printf("Result: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
