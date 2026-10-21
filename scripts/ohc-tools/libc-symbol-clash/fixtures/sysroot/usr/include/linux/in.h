/* fixture: UAPI 侧 <linux/in.h>（复现 CLASH-005: struct in_addr 同名） */
#ifndef _FIXTURE_LINUX_IN_H
#define _FIXTURE_LINUX_IN_H

#include <linux/socket.h>

struct in_addr {
    unsigned int s_addr;
};

#endif /* _FIXTURE_LINUX_IN_H */
