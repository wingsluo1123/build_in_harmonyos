/*
 * test_package/test.c — uanytun 消费者视角验证（R34：必须真实调用被测包）
 *
 * 通过 conanrun 环境提供的 PATH 定位安装好的 uanytun 二进制并执行：
 *   1) `uanytun -v` 退出码为 0 且输出包含 "uanytun version 0.3.7"
 *   2) `uanytun -h` 退出码为 0 且输出非空（证明命令行前端可运行）
 * 二进制缺失、损坏或版本错误时该测试失败。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 读取子进程全部输出后再 pclose：只读前 N 字节就关管道会让还在写用法文本的
 * 子进程收到 SIGPIPE（exit 141），把正常的 --help 误判成失败。 */
static int run_and_capture(const char *cmd, char *buf, size_t bufsize,
                           int *exit_code)
{
    FILE *p;
    char sink[512];
    size_t n, total = 0;

    p = popen(cmd, "r");
    if (p == NULL) {
        fprintf(stderr, "FATAL: cannot spawn '%s' from PATH\n", cmd);
        return -1;
    }
    while (total + 1 < bufsize &&
           (n = fread(buf + total, 1, bufsize - 1 - total, p)) > 0) {
        total += n;
    }
    buf[total] = '\0';
    /* 抽干剩余输出，避免子进程因管道提前关闭而收到 SIGPIPE */
    while (fread(sink, 1, sizeof(sink), p) > 0) {
        /* discard */
    }
    *exit_code = pclose(p);
    return 0;
}

int main(void)
{
    char buf[4096];
    int rc = 0;

    if (run_and_capture("uanytun -v", buf, sizeof(buf), &rc) != 0)
        return 1;
    if (rc != 0) {
        fprintf(stderr, "FATAL: 'uanytun -v' exited with status %d\n", rc);
        return 1;
    }
    if (strstr(buf, "uanytun version 0.3.7") == NULL) {
        fprintf(stderr, "FATAL: unexpected 'uanytun -v' output: '%s'\n", buf);
        return 1;
    }
    printf("[ok] uanytun -v -> %s", buf);

    if (run_and_capture("uanytun -h", buf, sizeof(buf), &rc) != 0)
        return 1;
    if (rc != 0) {
        fprintf(stderr, "FATAL: 'uanytun -h' exited with status %d\n", rc);
        return 1;
    }
    if (strstr(buf, "uanytun") == NULL || strstr(buf, "USAGE") == NULL) {
        fprintf(stderr, "FATAL: 'uanytun -h' produced no usage text\n");
        return 1;
    }
    printf("[ok] uanytun -h produced usage text (%u bytes)\n",
           (unsigned)strlen(buf));

    return 0;
}
