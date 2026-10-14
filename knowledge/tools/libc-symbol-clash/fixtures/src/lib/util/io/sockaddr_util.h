/* fixture: 项目内头文件，间接把 libc 侧 <sys/socket.h> 带进来（transitive include 解析） */
#ifndef _FIXTURE_SOCKADDR_UTIL_H
#define _FIXTURE_SOCKADDR_UTIL_H

#include <sys/socket.h>

static inline int fixture_sockaddr_family(const struct sockaddr *sa) {
    return (int)sa->sa_family;
}

#endif /* _FIXTURE_SOCKADDR_UTIL_H */
