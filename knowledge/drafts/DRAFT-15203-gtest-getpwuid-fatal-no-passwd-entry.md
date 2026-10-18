# DRAFT-15203: 容器 uid 不在 /etc/passwd 时 g_test 二进制 FATAL 启动崩溃（纯 C shim 解法）

> 状态: **草稿**（待审核 promote） | severity: `P1` | category: `platform` | 更新: 2026-10-16
> 对应 kv: `knowledge/drafts/DRAFT-15203-gtest-getpwuid-fatal-no-passwd-entry.kv`

---

**匹配关键词**: getpwuid_r, g_get_user_name, passwd, Signal 6, LD_PRELOAD, Error relocating, g_test, TAP

## 错误特征 (error_signature)

```text
Bail out!
Signal 6 (core dumped)
TAP version 14 + # random seed 后无任何用例输出
```

## 错误摘录 (error_excerpt)

```text
TAP version 14
# random seed: R02S...
Bail out!
Signal 6 (core dumped)
# 子进程（若 shim 带 glib 符号）:
Error relocating /bin/sh: g_content_type_set_mime_dirs: symbol not found   (rc=127)
```

## 根因 (root_cause)

容器 uid（如 20020090）**不在 /etc/passwd**。g_test 二进制的 `main` 若调用
`g_get_user_name()` / `g_get_home_dir()`——例如 totem-plparser 测试 main 的
`check_http()`（tests/utils.c:268 `g_strcmp0 (g_get_user_name (), "hadess")`）——
glib 的 `g_get_user_name_real` 在 `getpwuid_r` 失败时 **FATAL abort**：

- 进程在**注册用例之前**就死（Signal 6）
- 日志只有 TAP 头 + `# random seed` 行，零用例执行
- 任何单用例/全量运行都复现，表现为"测试根本没跑"

## 建议方案 (rec_approach)

LD_PRELOAD 纯 C `getpwuid_r` 拦截器：

```c
#define _GNU_SOURCE
#include <pwd.h>
#include <stdlib.h>
int getpwuid_r (uid_t uid, struct passwd *pwd, char *buf, size_t len, struct passwd **ret)
{
    pwd->pw_name = "user";
    pwd->pw_passwd = "x";
    pwd->pw_uid = uid;
    pwd->pw_gid = 0;
    pwd->pw_gecos = "";
    pwd->pw_dir = getenv("HOME") ? getenv("HOME") : "/";
    pwd->pw_shell = "/bin/sh";
    *ret = pwd;
    return 0;
}
```

```bash
clang -shared -fPIC shim.c -o libshim.so
nm -D libshim.so        # 验证：只导出 getpwuid_r，U 仅 libc 符号
LD_PRELOAD=$PWD/libshim.so HOME=$HOME ./test-binary
```

**两条硬约束**（均实测踩坑）：

1. **shim 的 .so 只能带 libc 符号**。LD_PRELOAD 被所有子进程继承——totem 的
   videosite 机制用 `g_spawn_sync` 派生 `/bin/sh` 跑 `videosite-tester.sh`，若 .so
   引用 glib 等子进程中不存在的符号 → `Error relocating /bin/sh: ...: symbol not
   found` → 脚本恒空返回（rc=127）→ 依赖 videosite 的 5 个用例全灭。
   （反例：同时注入 `g_content_type_set_mime_dirs` 的 shim 即触发此问题。）
2. **HOME 必须指向可写目录**（g_get_home_dir / 临时文件写入依赖）。

**与另一类失败的区分**：totem `check_http()` 本身有未初始化变量 bug
（tests/utils.c:265 `gboolean http_supported;` 未初始化）——GLocalVfs 无 http
scheme 时循环不置值，返回不可确定值（本机实测 TRUE），http 依赖测试因此**不会**
按注释意图自跳过，而是进入抓取分支后因 OHOS 无 http GFile 后端失败。该失败归因
"平台缺 http GFile 后端 + 上游测试依赖 2011 年代外部站点"，与本 shim 无关。

## 实测证据 (source)

- totem-pl 3.26.7 上游测试（g_test 二进制 parser/podcast/disc），OHOS 真机 aarch64，2026-10-16
- 无 shim：parser/podcast 首跑即 Signal 6（TAP 头后零用例）
- shim 带 glib 符号：videosite 5 用例 rc=127（/bin/sh relocation 错误）
- 纯 C shim（仅 getpwuid_r）：72/72 用例可执行，68 通过（剩余 4 失败归因见 DRAFT-15201
  关联的上游测试报告：glib 版本行为差 + http 后端缺失 + 外部站点腐化）
- disc 二进制另有一个上游门控：main 仅当 `g_get_user_name()=="hadess"` 时注册 2 个
  g_test 用例，其余用户直接 `return 0`（0 用例，rc=0）；位置参数模式
  `./disc <device>` 可直跑 test_disc（实测 /dev/dvd 与不存在路径均 rc=0，仅
  "No media in drive" 消息）
