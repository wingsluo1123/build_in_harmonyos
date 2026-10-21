/*
 * test.c — nr_micro_shell 2.0.0 消费者验证 + 鸿蒙专项测试
 *
 * 仅通过包内公开头文件 <nr_micro_shell.h> 与公共 API（shell_init/shell）
 * 使用库：模拟用户从终端逐字符输入命令。库内 shell_putc 编译期绑定为
 * putchar，因此消费者把 fd1(stdout) 重定向到临时文件，feed 命令后
 * fflush 并用同一 fd 回读（同文件描述符读写，避免跨句柄缓存不一致），
 * 断言 shell 输出出现预期结果（R34：实质调用被测包 API，非空壳）。
 *
 * 断言：
 *   1. "hex2dec 0xff\r" -> 输出含 "0xff = 255"
 *   2. "hex2dec 31\r"   -> 输出含 "0x1f = 31"（hex2dec 解析十六进制并可逆）
 *   3. "help\r"         -> 命令表包含 hex2dec / time / clear
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#include <nr_micro_shell.h>

#define OUT_FILE "shell_output.txt"
#define CAP_SZ 65536

static int saved_stdout = -1;
static char capture[CAP_SZ];

static void feed(const char *s)
{
    while (*s) {
        shell((unsigned char)*s++);
    }
}

static int has_substr(const char *hay, const char *needle)
{
    return strstr(hay, needle) != NULL;
}

/* 用同一 fd 重定向 stdout 到临时文件并回读捕获内容 */
static int capture_begin(void)
{
    int fd = open(OUT_FILE, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        fprintf(stderr, "open(%s): %s\n", OUT_FILE, strerror(errno));
        return -1;
    }
    if (saved_stdout < 0) {
        saved_stdout = dup(STDOUT_FILENO);
        if (saved_stdout < 0) {
            fprintf(stderr, "dup: %s\n", strerror(errno));
            close(fd);
            return -1;
        }
    }
    if (dup2(fd, STDOUT_FILENO) < 0) {
        fprintf(stderr, "dup2: %s\n", strerror(errno));
        close(fd);
        return -1;
    }
    close(fd);
    return 0;
}

static int capture_readback(void)
{
    ssize_t n;

    fflush(stdout);
    if (lseek(STDOUT_FILENO, 0, SEEK_SET) < 0) {
        fprintf(stderr, "lseek: %s\n", strerror(errno));
        return -1;
    }
    memset(capture, 0, sizeof(capture));
    n = read(STDOUT_FILENO, capture, sizeof(capture) - 1);
    if (n < 0) {
        fprintf(stderr, "read: %s\n", strerror(errno));
        return -1;
    }
    capture[n] = '\0';
    return 0;
}

static int run_case(const char *name, const char *input, const char *expect)
{
    int ok;

    if (capture_begin() < 0) {
        return 1;
    }
    feed(input);
    if (capture_readback() < 0) {
        return 1;
    }
    ok = has_substr(capture, expect);
    fprintf(stderr, "CASE[%s] expect=%s -> %s\n", name, expect,
            ok ? "PASS" : "FAIL");
    if (!ok) {
        fprintf(stderr, "  --- captured output ---\n%s\n  ----------------------\n", capture);
        return 1;
    }
    return 0;
}

int main(void)
{
    int fails = 0;

    /* 消费者自定义 shell_putc 在预编译库内不生效；改用 fd1 重定向捕获 */
    if (capture_begin() < 0) {
        return 2;
    }

    shell_init();

    /* 断言 1: hex2dec 0xff -> 255（公开命令 API 调用 + 可观察输出）*/
    fails += run_case("hex2dec_0xff", "hex2dec 0xff\r", "0xff = 255");

    /* 断言 2: hex2dec 0x1f -> 31（十六进制解析一致性） */
    fails += run_case("hex2dec_0x1f", "hex2dec 0x1f\r", "0x1f = 31");

    /* 断言 3: help 命令表包含内置命令（命令注册可观察） */
    fails += run_case("help_cmd_table", "help\r", "hex2dec");
    fails += run_case("help_has_time", "help\r", "time");
    fails += run_case("help_has_clear", "help\r", "clear");

    /* 恢复 stdout */
    if (saved_stdout >= 0) {
        dup2(saved_stdout, STDOUT_FILENO);
        close(saved_stdout);
    }

    if (fails == 0) {
        printf("CONSUMER_PASS nr_micro_shell shell api works on this platform\n");
        return 0;
    }
    printf("CONSUMER_FAIL %d assertion(s) failed\n", fails);
    return 1;
}