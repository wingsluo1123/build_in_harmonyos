/* fixture: rtnetlink（include 链把 UAPI 侧 sockaddr 定义带进来） */
#ifndef _FIXTURE_LINUX_RTNETLINK_H
#define _FIXTURE_LINUX_RTNETLINK_H

#include <linux/socket.h>

#define RTM_NEWLINK 16
#define RTM_DELLINK 17

#endif /* _FIXTURE_LINUX_RTNETLINK_H */
