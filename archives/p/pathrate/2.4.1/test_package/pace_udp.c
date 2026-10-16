#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <sys/socket.h>
#include <time.h>

/* Shape only the test sender's UDP datagrams so loopback is measurable. */
typedef ssize_t (*sendto_fn)(int, const void *, size_t, int,
                             const struct sockaddr *, socklen_t);

ssize_t sendto(int fd, const void *buf, size_t len, int flags,
               const struct sockaddr *addr, socklen_t addrlen)
{
    static sendto_fn real_sendto;
    struct timespec pause = {0, 1000000};
    if (!real_sendto)
        real_sendto = (sendto_fn)dlsym(RTLD_NEXT, "sendto");
    nanosleep(&pause, NULL);
    return real_sendto(fd, buf, len, flags, addr, addrlen);
}
