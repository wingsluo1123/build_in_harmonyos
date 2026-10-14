/* fixture: 合成 UAPI 侧 <linux/socket.h>（模拟 bionic 派生内核头：无 __GLIBC__ 互斥） */
#ifndef _FIXTURE_LINUX_SOCKET_H
#define _FIXTURE_LINUX_SOCKET_H

#include <sys/socket.h>

/* 真实 sysroot 的 UAPI 侧只重复定义部分结构（kea 3.0.3 实证：仅 sockaddr_storage 冲突），
   fixture 因此只保留该结构 —— 用于验证 --sysroot 实测会剔除未复现的候选。 */
struct sockaddr_storage {
    unsigned short ss_family;
    char __data[126];
};

#endif /* _FIXTURE_LINUX_SOCKET_H */
