/* fixture: libc 侧 <net/if.h>（真实 musl 会拉入 <sys/socket.h> 的定义） */
#ifndef _FIXTURE_NET_IF_H
#define _FIXTURE_NET_IF_H

#include <sys/socket.h>

#define IFNAMSIZ 16

struct ifreq {
    char ifr_name[IFNAMSIZ];
};

#endif /* _FIXTURE_NET_IF_H */
