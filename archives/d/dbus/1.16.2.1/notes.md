# 当前失败诊断的最小修改

原 auth-script:640 的 no memory for username 共享文案没有实际错误类型。
独立原完整 misc-r002 的 init_process_info 失败点实际输出 UID20020084、
org.freedesktop.DBus.Error.Failed、Looking up user ID 20020084: not found；
observer SHA256 08c156c0074f80638ed52f3e8f3dad47f8bc34b31214ebe698b66eec45edf848。
未命中 allocation、lock、string append 标识，组仍 ERROR/-6，不算 PASS。

当前源码 dbus/dbus-userdb.c 只在原 DBUS_ENABLE_EMBEDDED_TESTS 下增加
非 fatal stderr 实际 DBusError 诊断，随后原 error_free/return FALSE 不改，
原 auth-script fatal warning/断言保留。生产 intrusive=false 无该日志。
源码官方 refresh-patch --auto 输出只同步对应0004补丁。

native_upstream 仅接受 typed UID not found 加原640文案、完整49/RC/skip匹配，
旧共享warning单独、NoMemory和其他错误全部拒绝。默认接受配置仍关闭。
此改动使旧r003不能证明当前候选；下一fresh正式step35/49/4/1验证，
不修改任何旧freeze/receipt/marker或宣称完整49PASS。

## 原子进程回收的目标修复（2026-10-11）

正式 r007 的原 dbus-daemon 组记录 TIMEOUT/300 秒，即使 stdout 已包含
原 36 项结束标记也仍不算通过。日志反复出现 GLib pidfd signaled but pid
didn't exit；保留这个真实失败，不归入 NSS 能力豁免。
仅在 __OHOS__ 下将 test_kill_pid 对自己 spawn 得到的精确子 PID 改为
原 SIGTERM 后的真实 waitpid，重试 EINTR、校验回收 PID 和真实终态。
不扫描或影响其他任务进程、不延长原超时、不改原测试注册及断言。
这只是针对目标回收症状的修复候选，必须由 fresh 正式事务验证效果；
不追认 r007、旧 marker 或旧上游结果。

fresh 正式 oct11-r008 已真实完成原49组，不再有 TIMEOUT；原 daemon 组 OK
仍包含两个权限 SKIP。整体44 clean/1partial/3ERROR/1wholeSKIP，官方 step35
RC0、consumer4/Harmony1。observer SHA256
20d62345acf90637b84cd8cbe82409882c018b4991eeb1c725e82ec30599711f。
自有子进程真实回收修复与账户限制独立，不以能力豁免解释旧超时，不称49/49。
