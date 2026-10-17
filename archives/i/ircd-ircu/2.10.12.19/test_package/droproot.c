/*
 * test_package/droproot.c -- run a command with a non-zero uid/gid.
 *
 * ircd refuses to start when any of uid/euid/gid/egid is 0: ircd.c's
 * set_userid_if_needed() prints "ERROR:  This server will not run as
 * superuser." and main() returns 3, for -k as well as for the live daemon.
 * The OHOS CI worker already runs as an unprivileged HMDFS uid, but the local
 * gate runs as root, and OHOS has neither setpriv/runuser/su nor a guaranteed
 * "nobody" entry in /etc/passwd, so drop privileges here instead.
 *
 * Two strategies, in order:
 *
 *   1. User namespace: unshare(CLONE_NEWUSER) and map the caller's outer uid 0
 *      onto an inner 65534. The kernel reverse-maps through the namespace for
 *      every file access check, so the child keeps full read/write access to
 *      everything the caller owns while getuid() reports 65534.
 *
 *   2. Plain setgid()/setuid(). Real DAC then applies, which would hide the
 *      conan package folder and this test_package's own directory behind a
 *      0700 home, so add the "search" bit (S_IXOTH, never S_IROTH) to the
 *      directories leading to both executables first. Search-only on a
 *      directory leaks no file contents and no directory listing.
 *
 * When the caller is already unprivileged both steps are skipped and the
 * command is exec'd unchanged.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef DROPROOT_ID
#define DROPROOT_ID 65534
#endif

/* Best effort: a namespace may already have /proc unmounted or be read-only. */
static void put_proc(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY);
    if (fd < 0)
        return;
    if (write(fd, value, strlen(value)) < 0)
        return;
    close(fd);
}

static int grant_search(const char *path)
{
    char buf[4096];
    struct stat st;

    if (strlen(path) >= sizeof(buf))
        return -1;
    snprintf(buf, sizeof(buf), "%s", path);

    for (;;) {
        char *slash = strrchr(buf, '/');
        if (slash == NULL)
            return 0;               /* relative path: nothing above it to fix */
        if (slash == buf)
            buf[1] = '\0';           /* the root directory itself */
        else
            *slash = '\0';

        if (stat(buf, &st) != 0)
            return -1;
        if ((st.st_mode & S_IXOTH) == 0) {
            if (chmod(buf, (mode_t)(st.st_mode | S_IXOTH)) != 0)
                return -1;
            printf("droproot: added search permission on %s\n", buf);
            fflush(stdout);
        }
        if (buf[0] == '/' && buf[1] == '\0')
            return 0;
    }
}

static int is_unprivileged(void)
{
    return getuid() != 0 && geteuid() != 0 && getgid() != 0 && getegid() != 0;
}

int main(int argc, char **argv)
{
    gid_t gid = DROPROOT_ID;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <command> [args...]\n", argv[0]);
        return 2;
    }

    if (!is_unprivileged()) {
        int in_userns = 0;

        if (geteuid() == 0 && unshare(CLONE_NEWUSER) == 0) {
            put_proc("/proc/self/setgroups", "deny\n");
            put_proc("/proc/self/uid_map", "65534 0 1\n");
            put_proc("/proc/self/gid_map", "65534 0 1\n");
            in_userns = 1;
        }

        if (!in_userns) {
            if (grant_search(argv[0]) != 0 || grant_search(argv[1]) != 0) {
                fprintf(stderr, "droproot: cannot grant search access to %s / %s\n",
                        argv[0], argv[1]);
                return 3;
            }
            if (geteuid() == 0 && setgroups(1, &gid) != 0) {
                perror("droproot: setgroups");
                return 3;
            }
            if (setgid(gid) != 0) {
                perror("droproot: setgid");
                return 3;
            }
            if (setuid(DROPROOT_ID) != 0) {
                perror("droproot: setuid");
                return 3;
            }
        }

        if (!is_unprivileged()) {
            fprintf(stderr, "droproot: could not drop privileges\n");
            return 3;
        }
    }

    execvp(argv[1], argv + 1);
    fprintf(stderr, "droproot: cannot execute %s: %s\n", argv[1], strerror(errno));
    return 127;
}