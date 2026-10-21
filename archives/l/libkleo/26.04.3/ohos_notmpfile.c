/* Test-only helper. HarmonyOS tmpfs accepts O_TMPFILE but linkat() does not
 * give the file a name, so QTemporaryFile::fileName() is empty and
 * Kleo::classify() returns 0. Rejecting O_TMPFILE makes Qt fall back to a
 * named file. The full O_TMPFILE mask is tested so O_DIRECTORY is left alone.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <unistd.h>

#ifndef O_TMPFILE
#define O_TMPFILE (020000000 | 0200000)
#endif

static int block_tmp(int flags)
{
    return (flags & O_TMPFILE) == O_TMPFILE;
}

int open(const char *path, int flags, ...)
{
    static int (*real_open)(const char *, int, ...) = 0;
    mode_t mode = 0;
    if (!real_open)
        real_open = dlsym(RTLD_NEXT, "open");
    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (block_tmp(flags)) {
        errno = EOPNOTSUPP;
        return -1;
    }
    if (flags & O_CREAT)
        return real_open(path, flags, mode);
    return real_open(path, flags);
}

int openat(int dirfd, const char *path, int flags, ...)
{
    static int (*real_openat)(int, const char *, int, ...) = 0;
    mode_t mode = 0;
    if (!real_openat)
        real_openat = dlsym(RTLD_NEXT, "openat");
    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (block_tmp(flags)) {
        errno = EOPNOTSUPP;
        return -1;
    }
    if (flags & O_CREAT)
        return real_openat(dirfd, path, flags, mode);
    return real_openat(dirfd, path, flags);
}
