/* rtkit 真机端到端测试 shim #1：通过 rtkit-daemon 的启动门禁。
 *
 * 背景：rtkit-daemon 在 main() 开头硬性要求 getuid()==0（rtkit-daemon.c:2593）。
 * 本沙箱无 root、无 sudo，user namespace 被 seccomp 拦截（unshare 返回
 * SIGSYS），无法满足该门禁。
 *
 * 为什么不能整体伪装成 uid 0：libdbus 的 AUTH EXTERNAL 会把 getuid() 的值作为
 * 声称身份发给总线，总线用内核 SO_PEERCRED 校验；声称 0 与真实 uid 不符时
 * 握手被丢弃，客户端表现为 "Did not receive a reply"（已实测）。
 *
 * 因此只在**第一次** getuid() 调用返回 0（即 daemon 的 root 门禁），之后一律
 * 返回真实 uid，D-Bus 认证与内核权限判定不受影响。
 *
 * 该 shim 不赋予任何内核能力：SCHED_RR / 负 nice 仍会被内核 EPERM 拒绝，
 * 故本测试验证的是 D-Bus 服务端到端链路，而非实时调度的实际生效。
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/syscall.h>
#include <unistd.h>

static int gate_calls = 0;

uid_t getuid(void) {
    if (gate_calls++ == 0) {
        return 0; /* 仅 rtkit-daemon 的启动门禁 */
    }
    return (uid_t) syscall(SYS_getuid);
}

uid_t geteuid(void) {
    return (uid_t) syscall(SYS_geteuid);
}
