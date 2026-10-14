/* Exact native exec trampoline; no authentication or assertion substitution. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#ifndef HARNESS_EXECUTABLE
#error HARNESS_EXECUTABLE must name the actual original binary
#endif
#ifndef HARNESS_LIBRARY_PATH
#error HARNESS_LIBRARY_PATH must name the process-private provider closure
#endif
int main(int argc, char **argv)
{
    if (argc < 1 || argv == NULL || argv[0] == NULL) return 125;
    if (setenv("LD_LIBRARY_PATH", HARNESS_LIBRARY_PATH, 1) != 0) {
        perror("private runtime"); return 125;
    }
    argv[0] = (char *)HARNESS_EXECUTABLE;
    execv(HARNESS_EXECUTABLE, argv);
    int saved_errno = errno;
    perror("native exec");
    return saved_errno == ENOENT ? 127 : 126;
}
