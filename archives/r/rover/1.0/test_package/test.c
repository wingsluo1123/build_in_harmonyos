#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 消费者视角验证：执行被测包安装出来的 rover 二进制。 */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL: no rover binary path provided\n");
        return 1;
    }

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" -v 2>&1", argv[1]);

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("FAIL: popen() failed\n");
        return 1;
    }

    char buf[256];
    memset(buf, 0, sizeof(buf));
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    int rc = pclose(fp);

    if (rc != 0) {
        printf("FAIL: rover -v exited with %d\n", rc);
        return 1;
    }
    if (n == 0 || strstr(buf, "rover") == NULL) {
        printf("FAIL: unexpected version output: '%s'\n", buf);
        return 1;
    }

    printf("test rover 1.0: OK (%s)\n", buf);
    return 0;
}
