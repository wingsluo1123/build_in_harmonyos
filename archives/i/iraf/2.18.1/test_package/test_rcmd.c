#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern int iraf_rcmd_ssh(char **, int, const char *, const char *, const char *, int *);

static int read_text(int fd, char *buffer, size_t size)
{
    size_t used = 0;
    while (used + 1 < size) {
        ssize_t n = read(fd, buffer + used, size - used - 1);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return -1;
        if (!n) break;
        used += (size_t)n;
    }
    buffer[used] = 0;
    return 0;
}

static int check(int separate)
{
    char *host = "iraf-fixture.invalid";
    char output[256], error[256];
    int errfd = -1;
    int inherited[2];
    char byte;
    if (pipe(inherited) < 0 || fcntl(inherited[0], F_SETFL, O_NONBLOCK) < 0)
        return 1;
    int fd = iraf_rcmd_ssh(&host, 512, "local", "fixture-user", "fixture-command",
                           separate ? &errfd : NULL);
    if (fd < 0) return 1;
    close(inherited[1]);
    if (read(inherited[0], &byte, 1) != 0) return 1;
    close(inherited[0]);
    if (write(fd, "ping\n", 5) != 5) return 1;
    if (read_text(fd, output, sizeof output)) return 1;
    close(fd);
    if (separate) {
        if (read_text(errfd, error, sizeof error)) return 1;
        close(errfd);
        if (strcmp(error, "ERR\n")) return 1;
        return strcmp(output, "READY\nECHO:ping\n") != 0;
    }
    return strcmp(output, "READY\nECHO:ping\nERR\n") != 0;
}

int main(void)
{
    if (check(0) || check(1)) return 1;
    errno = 0;
    if (iraf_rcmd_ssh(NULL, 0, "local", "remote", "cmd", NULL) != -1 || errno != EINVAL)
        return 1;
    char *host = "iraf-fixture.invalid";
    if (setenv("KSRSH", "/iraf-nonexistent-transport", 1)) return 1;
    errno = 0;
    if (iraf_rcmd_ssh(&host, 512, "local", "remote", "cmd", NULL) != -1 || errno != ENOENT)
        return 1;
    puts("IRAF_SSH_CHANNEL=5/5");
    return 0;
}
