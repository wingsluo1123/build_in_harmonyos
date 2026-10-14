// fixture: 已修复形态（kea 3.0.3 补丁 0002 的 guard 写法，见 knowledge/tools/libc-symbol-clash/libc-detection-guard.md 形态 A）
// 检测器应把该 TU 的 CLASH-001 降级为 LOW（默认阈值下不报红），体现"修复后能判绿"。
#include <util/io/sockaddr_util.h>
#include <net/if.h>

#if defined(__linux__) && !defined(__GLIBC__)
#  define sockaddr_storage __linux_uapi_sockaddr_storage
#  define FIXTURE_RESTORE_SOCKADDR_STORAGE 1
#endif
#include <linux/rtnetlink.h>
#ifdef FIXTURE_RESTORE_SOCKADDR_STORAGE
#  undef sockaddr_storage
#  undef FIXTURE_RESTORE_SOCKADDR_STORAGE
#endif

int fixture_patched(void);
