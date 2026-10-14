# fixture：libc × 内核 UAPI 同名符号冲突（合成样例库）

供 `tests/test_libc_symbol_clash.py` 与 `knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py` 自测使用。
**全部合成**：不依赖真实 sysroot、不联网、不读 conan 缓存，在干净机器/OHOS aarch64 上行为一致。

## 目录

| 路径 | 作用 | 期望 |
| --- | --- | --- |
| `sysroot/usr/include/sys/socket.h` | 合成 libc 侧定义（`sockaddr_storage`/`sockaddr`/`msghdr`） | `sysroot` 模式实测两侧同名 |
| `sysroot/usr/include/linux/socket.h` | 合成 UAPI 侧（bionic 派生：无 `__GLIBC__` 互斥，且 include libc 头）；只重复定义 `sockaddr_storage`（对齐 kea 实证） | `sysroot` 模式命中 `CLASH-001` |
| `sysroot/usr/include/linux/rtnetlink.h` | 经 include 链把 UAPI 侧定义带进 TU | `includes` 模式的 UAPI 触发器 |
| `sysroot/usr/include/net/if.h` | 合成 libc 侧（真实 musl 会拉入 `sys/socket.h`） | `includes` 模式的 libc 触发器 |
| `sysroot/usr/include/netinet/in.h` × `linux/in.h` | `struct in_addr` 两侧同名 | `CLASH-005` |
| `src/lib/dhcp/iface_mgr_linux.cc` | **kea 形态**：`<net/if.h>` + `<linux/rtnetlink.h>` + 经项目头间接 `<sys/socket.h>` | 命中 `CLASH-001`（HIGH）等 4 条候选 |
| `src/lib/util/io/sockaddr_util.h` | 项目内头，间接引入 libc 头（验证 transitive 解析） | 为上条提供 libc 侧证据 |
| `src_clean/lib/clean.cc` | 对照组：只含 libc 头 | **零命中**（退出码 0） |
| `src_selfdefs/bad.cc` | 项目自身重定义 `struct sockaddr_storage` | `source` 模式命中 |
| `src_patched/lib/dhcp/iface_mgr_linux.cc` | **已修复形态**（kea 补丁 0002 的 guard 写法） | `includes --sysroot` 下 `CLASH-001` 降级 `LOW`(guarded)，退出码 0 |
| `patch-samples/0001-bad-platform-macro.patch` | 反例：新增行 `#if defined(__OHOS__)` | `lint` 命中 `GUARD-001`（HIGH） |
| `patch-samples/0002-good-libc-probe.patch` | 正例：`!defined(__GLIBC__)` 探针 + rename/undef | `lint` **零命中** |
| `patch-samples/0003-real-kea-3.0.3-sockaddr-storage.patch` | 真实样例（Kea 3.0.3 归档补丁副本） | `lint` **零命中**（真实世界正例） |

## 真实样例出处

`0003-real-kea-3.0.3-sockaddr-storage.patch` 与
`archives/k/kea-hook-host-cmds/3.0.3/patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch`
**逐字节一致**：

```
sha256 = a19a64b5556510e15c3d8ce488841375afe258f4d728bb35293a9f6ace1ae8b0
```

Kea 3.0.3 的 `src/lib/dhcp/iface_mgr_linux.cc` 同时包含 `<net/if.h>`（libc 侧
`struct sockaddr_storage`）与 `<linux/rtnetlink.h>`（UAPI 侧同名结构），在 OpenHarmony 的
musl 派生 sysroot 上报重定义；归档补丁以 libc 鉴别探针重命名内核侧定义修复。
自测套件固定校验该 sha256，防止样例被悄悄改写而失去"真实世界正例"的意义。

## 运行

```bash
# 全部断言
python3 tests/test_libc_symbol_clash.py
# 或经全量回归
python3 tests/run_all.py

# 手工复现（无需 sysroot）
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py includes --src knowledge/tools/libc-symbol-clash/fixtures/src
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py sysroot  --sysroot knowledge/tools/libc-symbol-clash/fixtures/sysroot
python3 knowledge/tools/libc-symbol-clash/detect-libc-symbol-clash.py lint     --patches knowledge/tools/libc-symbol-clash/fixtures/patch-samples
```
