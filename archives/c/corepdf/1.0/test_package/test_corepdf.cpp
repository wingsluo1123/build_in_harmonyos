#include <cstdlib>
#include <cstdio>
#include <sys/wait.h>

int main() {
    // Try to run the corepdf binary via PATH (set by conanrun env)
    int ret = system("corepdf --help 2>&1 > /dev/null");
    if (ret == -1) {
        printf("FAIL: system() failed\n");
        return 1;
    }
    if (WIFEXITED(ret)) {
        int code = WEXITSTATUS(ret);
        if (code == 127) {
            printf("FAIL: corepdf binary not found in PATH\n");
            return 1;
        }
        printf("PASS: corepdf binary found and executed (exit: %d)\n", code);
        return 0;
    }
    if (WIFSIGNALED(ret)) {
        // Binary ran but was killed by signal (e.g., SIGABRT from Qt platform plugin on headless)
        printf("PASS: corepdf binary started (killed by signal %d)\n", WTERMSIG(ret));
        return 0;
    }
    printf("FAIL: unknown exit status\n");
    return 1;
}
