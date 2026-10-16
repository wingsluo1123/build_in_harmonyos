/*
** redir.c - LD_PRELOAD shim that rewrites the SNPP port of outgoing connections.
**
** The qpage client always connects to the SNPP port compiled into the binary
** (444, or the "snpp" entry of /etc/services), and OHOS does not let an
** unprivileged process bind a port below 1024.  This shim intercepts connect()
** and rewrites a connection to TCP 444 into a connection to the port given by
** the QPAGE_SNPP_PORT environment variable, so the test can run its mock SNPP
** server on a high port without patching upstream.
**
** Build: cc -shared -fPIC redir.c -o redir.so
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdlib.h>

typedef int (*connect_fn)(int, const struct sockaddr *, socklen_t);

int connect(int fd, const struct sockaddr *addr, socklen_t len)
{
    static connect_fn real_connect = NULL;

    if (real_connect == NULL)
        real_connect = (connect_fn)dlsym(RTLD_NEXT, "connect");

    if (addr != NULL && addr->sa_family == AF_INET) {
        const char *env = getenv("QPAGE_SNPP_PORT");
        if (env != NULL) {
            struct sockaddr_in in = *(const struct sockaddr_in *)addr;
            if (ntohs(in.sin_port) == 444) {
                in.sin_port = htons((unsigned short)atoi(env));
                return real_connect(fd, (const struct sockaddr *)&in, sizeof(in));
            }
        }
    }
    return real_connect(fd, addr, len);
}
