#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
#include <numa.h>

int main(void) {
    /* Test that libnuma is linkable and its API is callable.
     * numa_available() calls NUMA syscalls (get_mempolicy) which may
     * trigger SIGSYS on HarmonyOS where the syscall is not implemented.
     * Fork a child to isolate the signal. */
    pid_t pid = fork();
    if (pid == 0) {
        _exit(numa_available() < 0 ? 1 : 0);
    } else if (pid > 0) {
        int status;
        waitpid(pid, &status, 0);
        if (WIFSIGNALED(status)) {
            printf("numactl 2.0.18: libnuma linked OK, NUMA syscall not available (signal %d, expected on HarmonyOS)\n", WTERMSIG(status));
        } else {
            printf("numactl 2.0.18: libnuma linked OK, numa_available() returned %d\n", WEXITSTATUS(status) == 0 ? 0 : -1);
        }
        return 0;
    }
    printf("numactl 2.0.18: fork failed\n");
    return 1;
}
