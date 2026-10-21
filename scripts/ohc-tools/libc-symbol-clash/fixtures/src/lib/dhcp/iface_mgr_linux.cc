// fixture: 复现 kea-hook-host-cmds 3.0.3 的冲突形态
//   <net/if.h>（libc）与 <linux/rtnetlink.h>（UAPI）同在一个编译单元 →
//   musl 派生 sysroot 上 struct sockaddr_storage 重定义。
#include <util/io/sockaddr_util.h>
#include <net/if.h>
#include <linux/rtnetlink.h>

int fixture_iface_mgr(void);
