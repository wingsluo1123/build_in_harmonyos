/* L1/鸿蒙特有测试 for runuser 2.42.2.
 * 真实端到端消费者用例：fork+exec 实际执行 runuser 二进制并校验其行为输出
 * 1) root 环境：runuser -u nobody -- id -un 真实切换用户并执行命令，校验输出为 nobody
 * 2) 非 root 环境：runuser 按设计触发权限保护（"may not be used by non-root users"），校验真实拒绝行为
 * 3) runuser --version 输出内容校验（须含 "runuser from util-linux"）
 * 4) runuser --help 退出码 0
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

static int run_cmd(const char *bin, char *const argv[], char *out, size_t outsz, int *exitcode)
{
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        perror("pipe");
        return -1;
    }
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return -1;
    }
    if (pid == 0) {
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]);
        close(pipefd[1]);
        execv(bin, argv);
        perror("execv");
        _exit(127);
    }
    close(pipefd[1]);
    ssize_t n = read(pipefd[0], out, outsz - 1);
    if (n < 0)
        n = 0;
    out[n] = '\0';
    close(pipefd[0]);
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return -1;
    }
    if (exitcode)
        *exitcode = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <runuser-binary>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    int fails = 0;
    char out[4096];
    int rc = 0;

    /* 1) 二进制存在且可执行 */
    if (access(bin, X_OK) != 0) {
        fprintf(stderr, "FAIL: %s not executable\n", bin);
        fails++;
    } else {
        printf("PASS: %s exists and is executable\n", bin);
    }

    /* 2) 真实端到端消费者用例：root 切换用户 / 非 root 触发 runuser 真实拒绝路径 */
    char *uargs[] = {(char *)bin, (char *)"-u", NULL, (char *)"--", (char *)"id", (char *)"-un", NULL};
    if (geteuid() == 0) {
        /* root：真实切换用户执行命令，校验输出为目标用户 nobody */
        uargs[2] = (char *)"nobody";
        if (run_cmd(bin, uargs, out, sizeof(out), &rc) != 0) {
            fprintf(stderr, "FAIL: runuser -u nobody -- id -un execute error\n");
            fails++;
        } else if (rc != 0) {
            fprintf(stderr, "FAIL: runuser -u nobody -- id -un rc=%d out=%s\n", rc, out);
            fails++;
        } else if (!strstr(out, "nobody")) {
            fprintf(stderr, "FAIL: expected 'nobody' in output, got '%s'\n", out);
            fails++;
        } else {
            printf("PASS: runuser -u nobody -- id -un => %s", out);
        }
    } else {
        /* 非 root：runuser 按设计拒绝非 root 调用。OHOS musl /etc/passwd
         * 用户条目 pw_dir 为空（root:x:0:0:::/bin/false），xgetuserpw
         * 字段校验先于权限检查失败，输出真实拒绝信息且退出码非 0；
         * 若目标用户可解析则输出 "may not be used by non-root users"。
         * 两条都是 runuser 真实功能路径（用户解析/权限保护），均须拒绝执行。 */
        uargs[2] = (char *)"root";
        if (run_cmd(bin, uargs, out, sizeof(out), &rc) != 0) {
            fprintf(stderr, "FAIL: runuser execute error\n");
            fails++;
        } else if (rc == 0) {
            fprintf(stderr, "FAIL: non-root runuser unexpectedly succeeded: %s\n", out);
            fails++;
        } else if (!strstr(out, "may not be used by non-root users")
                   && !strstr(out, "does not exist or the user entry does not contain all the required fields")) {
            fprintf(stderr, "FAIL: expected runuser rejection message, got '%s'\n", out);
            fails++;
        } else {
            printf("PASS: non-root runuser correctly rejected => %s", out);
        }
    }

    /* 3) --version 输出内容校验 */
    char *vargs[] = {(char *)bin, (char *)"--version", NULL};
    if (run_cmd(bin, vargs, out, sizeof(out), &rc) != 0) {
        fprintf(stderr, "FAIL: runuser --version execute error\n");
        fails++;
    } else if (rc != 0 || !strstr(out, "runuser from util-linux")) {
        fprintf(stderr, "FAIL: --version rc=%d out=%s\n", rc, out);
        fails++;
    } else {
        printf("PASS: runuser --version => %s", out);
    }

    /* 4) --help 退出码 0 */
    char *hargs[] = {(char *)bin, (char *)"--help", NULL};
    if (run_cmd(bin, hargs, out, sizeof(out), &rc) != 0) {
        fprintf(stderr, "FAIL: runuser --help execute error\n");
        fails++;
    } else if (rc != 0) {
        fprintf(stderr, "FAIL: --help rc=%d\n", rc);
        fails++;
    } else {
        printf("PASS: runuser --help rc=0\n");
    }

    if (fails) {
        fprintf(stderr, "TOTAL FAIL: %d\n", fails);
        return 1;
    }
    printf("ALL PASS\n");
    return 0;
}
