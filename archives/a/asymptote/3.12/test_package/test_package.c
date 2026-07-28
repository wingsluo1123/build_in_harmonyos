#include <stdio.h>
#include <string.h>
#include <sys/wait.h>

int main(void)
{
    char output[4096] = {0};
    size_t used = 0;
    FILE *pipe = popen("asy --version 2>&1", "r");

    if (pipe == NULL) {
        fprintf(stderr, "failed to execute asy --version\n");
        return 1;
    }

    while (used < sizeof(output) - 1 &&
           fgets(output + used, sizeof(output) - used, pipe) != NULL) {
        used = strlen(output);
    }

    int status = pclose(pipe);
    if (status == -1) {
        fprintf(stderr, "failed to close asy --version process\n");
        return 1;
    }
    if (WIFSIGNALED(status)) {
        fprintf(stderr, "asy --version terminated by signal: %d\n",
                WTERMSIG(status));
        return 1;
    }
    if (!WIFEXITED(status)) {
        fprintf(stderr, "asy --version did not report a normal exit\n");
        return 1;
    }
    if (WEXITSTATUS(status) != 0) {
        fprintf(stderr, "asy --version exited with code: %d\n",
                WEXITSTATUS(status));
        return 1;
    }
    if (strstr(output, "Asymptote") == NULL || strstr(output, "3.12") == NULL) {
        fprintf(stderr, "unexpected asy --version output: %s\n", output);
        return 1;
    }

    printf("validated packaged executable: %s", output);
    return 0;
}
