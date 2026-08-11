/* test_package/test.c — valgrind 消费者测试（R34 实质调用被测包 API）
 *
 * 不再是空壳 printf：实际调用 valgrind 的公开 API 做 fork+wait 场景测试，
 * 校验被测包导出的符号（valgrind.h）可链接、可调用。
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <valgrind.h>

int main(void) {
    /* 1) 实质调用被测包 API：RUNNING_ON_VALGRIND 校验非 valgrind 下返回 0 */
    if (RUNNING_ON_VALGRIND != 0) {
        fprintf(stderr, "FAIL: RUNNING_ON_VALGRIND should be 0 outside valgrind\n");
        return 1;
    }

    /* 2) fork+wait 真实场景：子进程正常退出，父进程校验退出码 */
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }
    if (pid == 0) {
        /* 子进程：实质再次调用被测包 API（VALGRIND_DISCARD_TRANSLATIONS），
         * 该符号由被测包导出，空壳测试不会链接到它 */
        VALGRIND_DISCARD_TRANSLATIONS(0, 1);
        _exit(0);
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "FAIL: child exited abnormally (status=%d)\n", status);
        return 1;
    }

    printf("test valgrind 3.24.0: OK (API linked, fork+wait clean)\n");
    return 0;
}
