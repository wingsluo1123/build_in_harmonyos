/* Independent fixture for a CLI whose batch mode does not need a terminal. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2) return 64;
    int interactive = strcmp(argv[1], "--interactive") == 0;
    int legacy = strcmp(argv[1], "--legacy") == 0;
    if (!interactive && !legacy && strcmp(argv[1], "--batch") != 0) return 64;

    int tty = open("/dev/tty", O_RDONLY);
    if (tty < 0) {
        int saved_errno = errno;
        if (legacy || interactive || isatty(STDOUT_FILENO)) {
            fprintf(stderr, "control terminal required: %s\n", strerror(saved_errno));
            return 2;
        }
        puts("batch payload");
        return 0;
    }
    close(tty);
    puts(interactive ? "interactive ready" : "batch payload");
    return 0;
}
