/* capprobe.c — procdump 2.2 上游测试执行层的**平台能力探测**（MR 15275 / rule4）。
 *
 * 目的：场景能否在本机真实执行，只取决于几项内核/平台能力。把这些能力连同
 * 原始证据（errno、/proc 内容、进程名）打印进构建日志，跳过才是有据的、可复核的，
 * 而不是「环境没装好」这类含糊说法。
 *
 * 探测项：
 *   1. euid            —— 上游 tests/integration/run.sh 强制 root；本包 0004 patch 放宽为
 *                         「同 uid ptrace」，故非 root 不构成阻塞，但如实记录。
 *   2. target_cmdline_argv0 —— 上游 GetProcessName()（src/Process.c:527）读 /proc/<pid>/cmdline
 *                         的 argv[0] 基名作为被监视进程名，并据此派生转储文件名。
 *                         在架构翻译层（qemu-user/binfmt）下 argv[0] 会变成解释器路径
 *                         （实测 /usr/libexec/qemu-binfmt/aarch64-binfmt-P），而 comm 仍是
 *                         guest 名 —— 因此必须按 cmdline 判定，不能按 comm。这是判定
 *                         「本环境结果不可信」的硬证据。
 *   2b. target_comm     —— 一并打印以便对照（翻译层下两者不一致即证明存在翻译层）。
 *   3. PTRACE_SEIZE    —— procdump 监视目标的手段（src/Monitor.c）。
 *   4. PTRACE_ATTACH   —— 备用 attach 路径。
 *   5. /proc/<pid>/mem —— 读目标内存（内存阈值判定 / 转储数据来源）。
 *
 * 退出码恒为 0：本程序只报告事实，不裁决；裁决由调用方读取上面的结论进行。
 * 这是探测程序，不是测试用例——它不产出自称的 PASS/FAIL。
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    char path[64];
    char buf[128];
    char argv0[256];
    int  fd;
    ssize_t n;
    pid_t ch;
    long  r;

    printf("euid=%d\n", (int)geteuid());

    ch = fork();
    if (ch < 0) {
        printf("fork=FAIL errno=%d (%s)\n", errno, strerror(errno));
        return 0;
    }
    if (ch == 0) {
        sleep(30);
        _exit(0);
    }
    sleep(1);

    /* 2. 被监视进程名 —— 必须按上游 GetProcessName()（src/Process.c:527）的口径读
     *    /proc/<pid>/cmdline 的 argv[0]，而不是 /proc/<pid>/comm：
     *    架构翻译层（qemu-user/binfmt）会把 comm 设成 guest 程序名（看起来正常），
     *    却把 argv[0] 换成解释器路径，从而漏判。这里两个都打印，便于对照。 */
    snprintf(path, sizeof(path), "/proc/%d/cmdline", (int)ch);
    argv0[0] = '\0';
    fd = open(path, O_RDONLY);
    if (fd >= 0) {
        n = read(fd, argv0, sizeof(argv0) - 1);
        close(fd);
        if (n > 0) {
            argv0[n] = '\0';
            /* cmdline 以 NUL 分隔，第一个字段即 argv[0] */
        }
    }
    {
        const char *slash = strrchr(argv0, '/');
        printf("target_cmdline_argv0=%s\n", argv0[0] ? argv0 : "<unreadable>");
        printf("target_argv0_basename=%s\n", argv0[0] ? (slash ? slash + 1 : argv0) : "<unreadable>");
    }
    snprintf(path, sizeof(path), "/proc/%d/comm", (int)ch);
    buf[0] = '\0';
    fd = open(path, O_RDONLY);
    if (fd >= 0) {
        n = read(fd, buf, sizeof(buf) - 1);
        close(fd);
        if (n > 0) {
            buf[n] = '\0';
            buf[strcspn(buf, "\n")] = '\0';
        }
    }
    printf("target_comm=%s\n", buf[0] ? buf : "<unreadable>");

    /* 3. PTRACE_SEIZE */
    errno = 0;
    r = ptrace(PTRACE_SEIZE, ch, (void *)0, (void *)0);
    printf("PTRACE_SEIZE=%s errno=%d (%s)\n", r == 0 ? "OK" : "FAIL", errno,
           r == 0 ? "-" : strerror(errno));
    if (r == 0) {
        ptrace(PTRACE_DETACH, ch, (void *)0, (void *)0);
    }

    /* 4. PTRACE_ATTACH */
    errno = 0;
    r = ptrace(PTRACE_ATTACH, ch, (void *)0, (void *)0);
    printf("PTRACE_ATTACH=%s errno=%d (%s)\n", r == 0 ? "OK" : "FAIL", errno,
           r == 0 ? "-" : strerror(errno));
    if (r == 0) {
        int st = 0;
        waitpid(ch, &st, 0);
        ptrace(PTRACE_DETACH, ch, (void *)0, (void *)0);
    }

    /* 5. /proc/<pid>/mem 可读性 */
    snprintf(path, sizeof(path), "/proc/%d/mem", (int)ch);
    errno = 0;
    fd = open(path, O_RDONLY);
    printf("proc_pid_mem=%s errno=%d (%s)\n", fd >= 0 ? "OK" : "FAIL", errno,
           fd >= 0 ? "-" : strerror(errno));
    if (fd >= 0) {
        char b[4];
        errno = 0;
        n = pread(fd, b, 1, 0);
        printf("proc_pid_mem_pread=%s errno=%d (%s)\n", n >= 0 ? "OK" : "FAIL",
               errno, n >= 0 ? "-" : strerror(errno));
        close(fd);
    }

    kill(ch, SIGKILL);
    waitpid(ch, NULL, 0);
    return 0;
}
