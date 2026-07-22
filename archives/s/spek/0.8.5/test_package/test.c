#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

int main(void) {
    // Test that spek-cli runs and produces help output
    int rc = system("spek-cli --help > /dev/null 2>&1");
    // POSIX: system() returns waitpid()-format status, not the exit code.
    // Extract the real exit code so CI sees failures correctly.
    int exit_code = WIFEXITED(rc) ? WEXITSTATUS(rc) : 1;
    if (exit_code == 0) {
        printf("spek-cli 0.8.5: OK\n");
    } else {
        printf("spek-cli 0.8.5: FAIL (exit %d)\n", exit_code);
    }
    return exit_code;
}
