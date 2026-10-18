#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 消费者用例：模拟上层桌面组件调用 rofi 对外公开 CLI（版本探针 rofi -v）。
 * 验证：编译通过、链接通过、调用运行通过（rofi 无需显示环境即可应答 -v）。 */
int main(void) {
    char buf[4096];
    FILE *fp = popen("rofi -v 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot popen rofi -v\n");
        return 1;
    }
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    int status = pclose(fp);
    if (status != 0) {
        fprintf(stderr, "FAIL: rofi -v exited with %d\noutput: %s\n", status, buf);
        return 1;
    }
    if (strstr(buf, "Version") == NULL) {
        fprintf(stderr, "FAIL: rofi -v output missing version: %s\n", buf);
        return 1;
    }
    printf("OK: consumer invoked rofi -v -> %s", buf);
    return 0;
}
