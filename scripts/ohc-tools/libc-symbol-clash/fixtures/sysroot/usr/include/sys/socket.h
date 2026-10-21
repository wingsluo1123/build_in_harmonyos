/* fixture: 合成 libc 侧 <sys/socket.h>（模拟 musl libc 定义） */
#ifndef _FIXTURE_SYS_SOCKET_H
#define _FIXTURE_SYS_SOCKET_H

typedef unsigned short sa_family_t;
typedef unsigned int socklen_t;

struct sockaddr {
    sa_family_t sa_family;
    char sa_data[14];
};

struct sockaddr_storage {
    sa_family_t ss_family;
    char __pad[126];
};

struct msghdr {
    void *msg_name;
    socklen_t msg_namelen;
};

#endif /* _FIXTURE_SYS_SOCKET_H */
