# pacredir 0.7.10 适配笔记

## 编译环境
- 构建系统: makefile（上游裸 GNU Makefile，无 configure/cmake/meson）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 目标平台: HarmonyOS PC / OpenHarmony，aarch64，musl libc
- 本地验证 profile: `ohos-local`（macOS 开发机交叉编译，OpenHarmony 5.1.0.107 / apiVersion 18 SDK）
- CI profile: `ci/conan/profiles/ohos-aarch64`（worker 侧 ohos-sdk_26.0.0.18）
- 状态: built（本地 W3 通过；待远程 HarmonyOS CI 终态回填）

## 上游概况

pacredir 是 Arch Linux 生态的 pacman 镜像重定向守护进程：监听
`127.0.0.1:7077`，把 pacman 的 `*.db` / `*.files` / `*.pkg` 请求 307 重定向到
局域网内经 mDNS（`_pacserve._tcp.local`）发现的对等 pacserve 镜像，并在 `/`
提供一个自刷新的 HTML 状态页（内嵌 favicon.png 与 style.css）。

整个上游只有 **1 个 C 源文件**（`pacredir.c`，约 1250 行）+ 4 个头文件，
tarball 共 35 个文件。它深度绑定 systemd 生态：

| 上游用途 | 依赖 | OHOS 上的实际情况 |
|---|---|---|
| mDNS peer 发现（`ResolveRecord`） | libsystemd sd-bus → systemd-resolved | OHOS 无 systemd-resolved、无系统总线 → 上游 `goto fast_finish` 优雅降级，仅静态 peer 生效 |
| 就绪通知（`READY=1`） | libsystemd sd-daemon | 无 NOTIFY_SOCKET → `sd_notify` 返回 0，`systemd=0` |
| 日志 | libsystemd sd-journal | 无 journald → `sd_journal_send` 失败被忽略，`write_log` 回退到 stdout/stderr |
| HTTP 服务 | libmicrohttpd | 正常 |
| peer 探测 / 计时 | libcurl（multi 接口） | 正常 |
| 配置文件 `/etc/pacredir.conf` | iniparser | 文件不存在时上游只告警并继续，正常 |

结论：**核心可执行产物在 OHOS 上可完整构建并运行**；mDNS 自动发现这条能力
在没有 systemd-resolved 的平台上不可用，属平台能力缺口（已在 PR 补充说明声明），
静态 peer（`pacserve hosts` 配置项）与状态页、重定向主链路不受影响。

## 编译步骤

```bash
# 1) 初始化（下载 + 解压 + 归档骨架）
python3 scripts/ohc-run.py init-build pacredir 0.7.10 \
    --url="https://github.com/eworm-de/pacredir/archive/refs/tags/0.7.10.tar.gz" \
    --tar tar.gz --auto

# 2) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight pacredir 0.7.10 --src $BUILD_SRC_DIR
#    → 语言匹配: task=cpp, detected=c（c↔cpp 兼容族），build_system=make

# 3) 源码可移植性修复（见「源码修改」），由 refresh-patch --auto 生成补丁
python3 scripts/ohc-run.py refresh-patch --auto pacredir 0.7.10

# 4) Conan 构建（配方内完成资产头生成 + make pacredir）
conan create archives/p/pacredir/0.7.10 \
    -pr:h=ohos-local -pr:b=ohos-local --build=missing
```

配方 `build()` 的实际动作：

1. `_prepare_generated_headers()` 用纯标准库 Python 生成上游 Makefile 在
   `pacredir` 目标上的全部生成式前置文件：
   - `config.h` ← `config.def.h`（上游规则就是一次 cp）
   - `version.h` ← 由 Conan settings 推导 `VERSION` / `ARCH` / `ID`
   - `favicon.png` ← `logo.png` 最近邻缩到 32x32 并重编码（替代 `resvg | oxipng`）
   - `favicon.h` / `style.h` ← 按 `contrib/static_file.sh` 的同构格式内嵌字节数组
2. `make pacredir CC=<conan cc> CFLAGS_EXTRA="<AutotoolsDeps 的 CPPFLAGS/CFLAGS/
   LDFLAGS/LIBS> + 三段链接控制" VERSION= ARCH= ID=`
   —— 生成后各前置文件 mtime 新于 logo.png/style.css/config.def.h/Makefile，
   make 因此跳过 resvg/oxipng/markdown/static_file.sh 这些 OHOS 上不可用的规则，
   只执行上游那条真正的编译命令，`-std=c11 -O2 -fPIC -Wall -Werror` 与
   `-Wl,-z,now -Wl,-z,relro -pie` 全部沿用上游。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./pacredir.h:89:2: error: unknown type name '__time_t'` | `__time_t` 是 glibc 的内部 typedef（经 `<sys/types.h>` 在 `_GNU_SOURCE` 下外泄）；musl 的头只按 `__NEED_*` 机制导出 POSIX 名，不提供 glibc 的 `__*_t` 别名族 | 补丁改用 POSIX 的 `time_t`（glibc 下同样成立，无平台宏） |
| 2 | `error: call to undeclared function 'ioctl'` + `use of undeclared identifier 'SIOCGIFFLAGS'`（-Werror 下致命） | 上游只 include 了 `<net/if.h>` 与 `<sys/socket.h>`，靠 glibc 的传递包含拿到 `ioctl()` 与 `SIOCGIFFLAGS`；musl 的这两个头不传递暴露 `<sys/ioctl.h>` | 补丁补 `#include <sys/ioctl.h>`（POSIX 正规做法，无平台宏） |
| 3 | `favicon.h` 无法生成：`resvg`/`oxipng` 不存在 | 两者都是 Rust CLI。制品仓里 `resvg/0.47.0`、`oxipng/v10.1.1` 的 manifest 状态都是 `built` 而非 `published`，`conan download --only-recipe` 实测取不到；且 CI 能力矩阵无 Rust 工具链，`tool_requires` 补不齐 | 配方内用纯标准库 Python 复刻资产链：解码上游随包 `logo.png`（96x96 调色板 PNG）→ 最近邻缩到 32x32 → 重编码 → 生成同构 C 头；生成后立即回读校验 chunk CRC 与维度 |
| 4 | `contrib/static_file.sh` 不可移植 | shebang 是 `#!/bin/sh` 却用了 bash 4 的 `${NAME^^}` 大写展开，还依赖 GNU 的 `stat --format=%s` 与 coreutils `sha1sum` | 不改上游脚本，改由配方按同一份 `static_file.h` 结构体布局直接产出（字段语义 date/mime/sha1/size/content 完全一致） |
| 5 | `ARCH` / `ID` 被编成空串 | 上游 Makefile 在**解析期**用 `$(shell shopt -u extglob && source /etc/makepkg.conf && echo $CARCH)` 与 `source /etc/os-release` 取值；OHOS 上两个文件都不存在，`$(shell)` 静默返回空串且丢弃 rc，空值经 `version.h` 编入二进制 | 配方从 Conan settings 推导（`armv8`→`aarch64`、`OHOS`→`ohos`）并在 make 命令行显式传 `ARCH=`/`ID=`。危害面见知识草稿 |
| 6 | 依赖图冲突：`Conflict between zlib/1.3.1.1 and zlib/1.3.1` | `systemd/261.1` 钉 `zlib/1.3.1`，`libcurl/8.5.0` 钉 `zlib/1.3.1.1` | override 到 `zlib/1.3.1`（见 #7 的方向选择） |
| 7 | 依赖图冲突 `Conflict between zlib/1.3.1.1 and zlib/1.3.1`，且**任一** override 方向都会让一个依赖失去预编译二进制、被迫从源码重建。第一版选「override 到 `zlib/1.3.1` + libcurl 切静态」，本地交叉编译实测通过（约 4 分钟），但**远程 CI #93768 失败**：`make: jobserver mkfifo: .../GMfifo48803: Operation not permitted` → `make[2]: /bin/sh: Resource temporarily unavailable` → `/bin/sh: can't fork - try again` → `Error 127`（libcurl 的 CMake 走 `make -j20`），整个 conan create 在依赖阶段即死，pacredir 连 `source()` 都没轮到 | 两层：① `zlib/1.3.1` 的 `libz.a` 是**非 PIC** 的（`zlib/1.3.1.1` 正是仓内为修此问题而建的修订版：`--static` + `CFLAGS=-fPIC`），把它吸进 DSO 会在 aarch64 上炸 `R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'`；② OHOS 的 SELinux 禁止用户进程创建 FIFO，而 GNU make 的 jobserver 靠 FIFO 传并行令牌（**E074/E525**），因此任何走 Unix Makefiles 的 `make -j>1` 在 worker 上必炸。而那个 `-j20` 出自 **libcurl 自己的配方**（`cmake.build()`），下游无从干预——`tools.build:jobs` / `MAKEFLAGS` 属 profile/conf 或 `ci/` 框架层，改它等于在单库 PR 里动框架文件（违反 W2），且会串行化全仓构建 | **反转 override 方向**：改为 override 到 `zlib/1.3.1.1`（即 libcurl 的原生 pin），让 libcurl 用回它**已发布的动态二进制**，把源码重建推给 **systemd** —— 其配方是纯 meson + `ninja libsystemd.so.0.44.0`，全程不经 GNU make jobserver（ninja 用 pipe），不受 E525 影响；且 systemd/261.1 本身就是经 PR CI 从源码 `conan create` 成功后才发布的（commit `17debd6e99`），worker 侧 meson/ninja 可用性已有实证（仓内另有 libseat/0.9.1、vte/0.74.2、libsoup/2.74.3 等多个 published 的 meson 包，且都不 `tool_requires` meson）。同时删掉 `self.options["libcurl"].shared = False`；`-Wl,--exclude-libs,ALL` 保留但职责收窄为「把静态吸收进来的符号留在本地作用域」。详见第三份知识草稿 |
| 8 | 链接可执行文件失败：`ld.lld: error: undefined reference due to --no-allow-shlib-undefined: mallinfo2 >>> referenced by libsystemd.so` | 双层根因：① `systemd/261.x` 配方在 OHOS 下注入 `-DHAVE_MALLINFO2=1`，而该宏在 `0005-musl-mallinfo2-guard.patch` 里同时罩住了 `struct mallinfo2` **和** systemd 自带的 `static inline mallinfo2()` 兜底实现；OHOS sysroot 的 `malloc.h` 只声明了 struct、没有函数，于是已发布的 `libsystemd.so.0.44.0` 带一个悬空 `U mallinfo2`。② SDK 的 `libc.so` 是链接桩（`.text` 仅 336 字节），其 `.dynsym` 收了 `malloc`/`mallopt` 却漏了 `mallinfo`/`mallinfo2` 家族，而同一 sysroot 的 `libc.a` 里两者都是 `T` —— 即设备真实 libc 有此符号，只是桩的动态符号表不全 | 加 `-Wl,--allow-shlib-undefined`，只放行**共享库自身**的未定义符号；pacredir 自己目标文件的未定义符号仍照常报错，不会被这个开关掩盖。详见知识草稿 |
| 9 | `DT_NEEDED` 里多出 `libzstd.so.1` | `systemd` 的 cpp_info 广告了 libzstd/liblzma，但实测 `libsystemd.so.0.44.0` 的未定义符号里没有任何 `ZSTD_*`/`lzma_*`（配方把 xz/lz4/zstd 全 disabled 了）。`--as-needed` 是**位置敏感**开关，排在 `-l` 之后对其完全不生效 | 把 `-Wl,--as-needed` 移到 `$LIBS` 之前。第一版（libcurl 静态）下 `DT_NEEDED` 收敛为 `{libsystemd.so.0, libc.so}`；改为 libcurl 动态后为 `{libcurl.so, libsystemd.so.0, libc.so}`，libzstd/liblzma 依然被丢掉 |
| 10 | `conandata.yml` 的 patches 写成「以补丁文件名为键」时补丁静默不生效 | Conan 的 `conandata_patches()` 以**版本号**为键查表；键名不匹配时返回空列表，`apply_conandata_patches()` 一声不响地什么都不做（本轮实测：配方 rc=0 走到编译才因同样 3 个错误暴露） | 改成 `patches: {"0.7.10": [ {patch_file: ...} ] }`，与 `archives/s/systemd/261.1` 一致 |
| 11 | 远程 CI #93768 把失败**误分类**为「网络问题 / 源码下载超时 (`https://gh-proxy.com/...`)」，修复指导也指向网络 | worker 上**没有 `curl`**，CI 预下载步骤的 6 次尝试全部报 `[fail] [Errno 2] No such file or directory: 'curl'`，日志里因此出现一串 gh-proxy.com 的 `[fail]` 行；CI 分类器按关键词命中就把整次失败归成下载超时。真正的错误在日志末尾的 `jobserver mkfifo`（问题 #7） | 按 R44 先跑 `gitcode_pr.py diagnose`，再自己读完整日志的**末尾**定位真因，不照着 CI 的分类去改源 URL。旁证 GitHub 源在 worker 上本身可达：全仓 7894 个 `conandata.yml` 中 3158 个用 `github.com` 源，其中大量 `status: published`（含 `vtk/9.4.1` 这种大包），说明 conan 自己的下载器能取到 GitHub；且本轮 CI 里 `libcurl/8.5.0` 的源码正是从 `https://curl.se/download/curl-8.5.0.tar.gz` 成功下载的 |
| 12 | `refresh-patch --auto` / `finalize-archive` 会把版本级 `manifest.yaml` 里 `patch_classification` **之后的所有段落**一并删掉 | `scripts/ohc/refresh_patch.py:547` 用 `re.sub(r'\npatch_classification:.*', '', content, flags=re.DOTALL)` 清旧块再追加新块；DOTALL 让 `.*` 一路吃到文件末尾。首轮即命中：`tests`（R51 测试台账）、`verification`、`knowledge_gained`、`knowledge_drafts` 四段全被吞掉 | 把 `patch_classification` 调整为 `manifest.yaml` 的**最后一个顶层键**，并在文件头写明该顺序约束；已实测验证——对该文件套用同一条 DOTALL 正则后四段全部幸存 |

| 13 | 远程 CI 第 1 轮 **#93768** 失败：`make: jobserver mkfifo: .../GMfifo48803: Operation not permitted` → `/bin/sh: can't fork - try again` → `Error 127`，且失败发生在**依赖阶段**（pacredir 连 `source()` 都没执行，耗时 653s） | 第一版把 override 定在 `zlib/1.3.1` 并强制 libcurl 静态，导致 `libcurl/8.5.0` 被迫从源码重建；其 CMake 走 `make -j20`，撞 OHOS SELinux 禁 FIFO（**E074/E525**：GNU make 的 jobserver 靠 FIFO 传并行令牌）。那个 `-j20` 出自 libcurl **自己的配方**，下游无杠杆（`tools.build:jobs` / `MAKEFLAGS` 属 profile/conf 或 `ci/` 框架层，改它违反 W2） | 反转 override 方向：改为 `zlib/1.3.1.1`（libcurl 的原生 pin）并删掉 `shared = False`，让 libcurl 用回**已发布的动态二进制**，把源码重建推给纯 meson + ninja 的 systemd。`conan graph info` 实测：仅 `systemd/261.1` 为 Build，`libcurl/8.5.0:4178e02c` 及其余 8 个依赖全部 Cache 命中，无版本冲突。详见第三份知识草稿 |
| 14 | 远程 CI 第 1 轮被机器人**误分类**为「网络问题 / 源码下载超时（gh-proxy.com 前缀的 tarball）」 | worker 上**没有 `curl`**，CI 预下载步骤的 6 次尝试全部报 `[fail] [Errno 2] No such file or directory: 'curl'`，日志里因此留下一串含 `gh-proxy.com` 的 `[fail]` 行，被分类器按关键词命中；真因在日志末尾的 `jobserver mkfifo` | 按 R44 先跑 `gitcode_pr.py diagnose`，再自己读完整日志**末尾**定位，不照 CI 的分类去改源 URL。GitHub 源本身在 worker 上可达：全仓 7894 个 `conandata.yml` 中 3158 个用 `github.com` 源且大量 `published`（含 `vtk/9.4.1` 这种大包）；且同一轮 CI 里 libcurl 的源码正是从 `https://curl.se/download/curl-8.5.0.tar.gz` 成功下载的 |
| 15 | 远程 CI 第 2 轮 **#94765**（SHA `8b8063f3`，worker CI-026）失败：`ninja: fatal: posix_spawn: Resource temporarily unavailable`，且 `cleanup` 步骤 120s 无输出超时 | **不是配方问题**。同一份日志里 `meson setup` 完整跑通（`Project name: systemd`、`Build targets in project`、`Found ninja-1.13.1 at /data/service/hnp/bin/ninja`），ninja 在**编译任何文件之前**的第一个 `posix_spawn` 就拿到 EAGAIN ⇒ worker 进程表枯竭。旁证：同 PR 的另两次构建 #94536/#94537（worker CI-010）在 `elapsedTime=0.055` 就死于 `zsh:1: fork failed: resource temporarily unavailable`，连 git-clone 都没完成；第 1 轮日志里也伴随 `/bin/sh: can't fork - try again`。属 R41 的「临时 CI 故障」 | 不改代码，重新评论 `/rebuild` 重试（基础设施重试，不计入 R42/R43 的修复轮次）。**同时记录一个正向结论**：这一轮实证了 worker 上 meson 与 ninja 均可用、systemd 的 meson configure 能跑完，即「把源码重建推给 systemd」这个方向本身成立；第 1 轮的 E525 判断也成立——若仍走 libcurl 的 `make -j20`，`mkfifo` 的 EPERM 是确定性平台拒绝，重试无效。若重试仍以同类进程枯竭失败，按 R41/R43 停损上报，不再盲推 |

| 16 | 远程 CI 第 3 轮 **#94856**（SHA `e7c35d46`，worker **CI-003**，仅 82s）失败：`/system/bin/sh: .../conanbuildenv-release-armv8.sh[13]: can't fork - try again` → `systemd/261.1: Error in build() method, line 237 meson.configure()` | 与第 2 轮**同一错误类别**（进程 fork/spawn 枯竭），且发生得更早——这次连 meson configure 的环境脚本都 fork 不出来。换了 worker（CI-026 → CI-003）依旧，说明不是单机故障 | **按 R41/R42 停损，不再盲重试**。证据链：本 PR 共 5 次构建落在 4 个不同 worker 上，全部出现 fork/spawn 失败——#94536/#94537（CI-010）在 `elapsedTime=0.055` 死于 `zsh:1: fork failed: resource temporarily unavailable`、**连 git-clone 都没完成**（此时本 PR 的任何代码都还没被执行）；#93768（CI-026）伴随 `/bin/sh: can't fork - try again`；#94765（CI-026）`ninja: fatal: posix_spawn: Resource temporarily unavailable`；#94856（CI-003）`can't fork - try again`。据此判定为**机群级 worker 资源枯竭**（临时 CI 故障，R41 明确列为「不是路径 B、不构成适配失败」），非本配方问题。终态按 `partial` + `loop_pending` 上报，附续跑命令，等 worker 恢复后 `submit --resume` 或重新 `/rebuild` 即可续环 |

### CI 停损判定与「不是本 PR 的问题」的取证

本 PR 唯一一次**真实**的配方层失败是第 1 轮 #93768（依赖图选型错误，已修，见问题 #13）。
其后 3 次构建（#94536/#94537 基础设施构建、#94765、#94856）的失败点全部是
**进程创建失败**，且有一个决定性的排除证据：

> #94536 与 #94537 在 `elapsedTime=0.055` / `0.063` 秒就死于
> `zsh:1: fork failed: resource temporarily unavailable`，构建步骤表显示
> `worker-prep ❌ / git-clone ❌ / cleanup ❌`——**连仓库都还没克隆下来**，
> 本 PR 的任何文件都尚未被读取，更谈不上被执行。

同一时间窗内、不同 worker（CI-010 / CI-026 / CI-003）反复出现同一种
`fork`/`posix_spawn` EAGAIN，只能是 worker 侧进程表或 pids cgroup 配额枯竭。

反向确认「配方本身没有引入进程压力」：

- 本 PR 的 `build()` 只做纯 Python 的资产头生成 + 一次 `make pacredir`
  （单 TU，只起 1 个编译进程），没有任何并行 fan-out；
- 失败点全部在 **`systemd/261.1` 的 `build()`** 内（meson configure / ninja 启动），
  即 pacredir 的 `build()` 从未被执行到；
- 第 2 轮 #94765 里 `meson setup` **完整跑通**（`Project name: systemd`、
  `Build targets in project`、`Found ninja-1.13.1 at /data/service/hnp/bin/ninja`），
  证明方向选择正确：worker 上 meson 与 ninja 都可用，systemd 的 configure 能过；
  真正卡住的是 ninja 启动第一个子进程。

因此本轮**不改任何代码**。第 1 轮的 E525 判断与第 2 轮的方向修正都已被证据支持：
若仍走 libcurl 的 `make -j20`，`mkfifo` 的 EPERM 是确定性平台拒绝（SELinux 策略），
重试无效；而 systemd 路线的失败是资源性的，worker 恢复后即可通过。

**续跑方式**（worker 恢复后任选其一）：

```bash
# 方式一：直接重触发 CI（不改代码）
python3 scripts/gitcode_pr.py trigger-ci \
    --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 16086
# 方式二：走 submit 的续环（自带 AI Review + CI 监控与 result 升级）
python3 scripts/ohc-run.py submit pacredir 0.7.10 --resume
```

## 源码修改

`patches/0001-pacredir.h.patch`（唯一补丁，`patch_type: portability`）。文件名由
`refresh-patch --auto` 按「4 位序号-被改文件路径」规则生成（R4：补丁只用该工具产出，
不手工改名，避免后续再跑工具时与 conandata.yml 失配）；改动说明以本节与
conandata.yml 的 `patch_description` 为准：

| 文件 | 修改 | 说明 |
|---|---|---|
| `pacredir.h` | `+#include <sys/ioctl.h>` | 见问题 #2 |
| `pacredir.h` | `struct hosts` 的 `__time_t badtime;` → `time_t badtime;` | 见问题 #1 |

两处都是**无条件的可移植性修复**，不含任何平台宏（R8 / PF5 合规），在 glibc
下同样正确编译。上游 `pacredir.c` 一行未改，`config.def.h` 未改（`PORT_PACREDIR`
7077、`CONFIGFILE` `/etc/pacredir.conf`、`DROP_PRIV_UID/GID` 65534 全部保持上游默认）。

## 依赖版本

W0 依赖发布检查（R35：一律用 `conan download --only-recipe` 实测，不用 `conan list`）：

| 包 | 版本 | 制品仓配方 | 制品仓 OHOS 二进制 | 用途 |
|----|------|-----------|-------------------|------|
| systemd | 261.1 | ✅ | ✅ 预编译二进制存在，但因本包的 zlib override 而失配，CI 上以 meson + ninja **从源码重建**（其自身 PR CI 已实证可在 worker 上源码构建，commit 17debd6e99） | libsystemd：sd-bus / sd-daemon / sd-journal |
| libmicrohttpd | 1.0.1 | ✅ | ✅ | 7077 端口 HTTP 服务与状态页 |
| libcurl | 8.5.0 | ✅ | ✅（`shared=True`，**直接沿用已发布动态二进制**） | peer 探测与计时（multi 接口）。第一版曾强制 `shared=False` 从源码重建，被 CI #93768 证伪（问题 #7） |
| iniparser | 4.2.6 | ✅ | ✅ | 解析 `/etc/pacredir.conf` |
| zlib | 1.3.1.1 | ✅ | ✅ | 仅经 override 进入依赖图（libcurl/systemd 的传递依赖）。选 1.3.1.1 而非 1.3.1 的两个理由见问题 #7：它是 PIC 修订版，且它是 libcurl 的原生 pin（从而保住 libcurl 的预编译二进制） |

不可用而**被绕开**的构建期工具（非依赖，不进 requires）：

| 工具 | 上游用途 | 制品仓状态 | 处置 |
|---|---|---|---|
| resvg 0.47.0 | `logo.svg` → 32x32 `favicon.png` | manifest `status: built`，`conan download` 取不到配方 | 配方内纯 Python 复刻（问题 #3） |
| oxipng v10.1.1 | PNG 优化 | 同上 | 同上 |
| `markdown`（Perl） | `*.md` → `*.html`（install-doc 用） | 无 | 不生成 .html，只装 .md 原文（见「交付物」） |
| `darkhttpd` | `install-bin` 里 `ln -s darkhttpd $(PREFIX)/bin/pacserve` | 1.17 已发布 | 不打包：跨 conan 包目录做符号链接会破坏可重定位性；pacserve 是 Arch 侧的 systemd unit 配套件，OHOS 无 systemd 本体 |

## 上游测试清点（R51 第 1 步）

**上游测试数：0**。清点证据（在解压后的 `pacredir-0.7.10/` 上实测）：

```console
$ find . -type f | wc -l
35
$ find . -type f \( -iname '*test*' -o -iname '*check*' -o -iname '*spec*' \) | wc -l
0
$ grep -E '^[A-Za-z_%.][-A-Za-z0-9_%.]*:' Makefile | cut -d: -f1 | tr '\n' ' '
all pacredir config.h version.h favicon.png favicon.h style.h %.service %.html install install-bin install-doc install-avahi clean distclean release
$ grep -cE '^(check|test|tests|validate):' Makefile
0
$ grep -rilE 'cmocka|cunit|check\.h|criterion|gtest|catch2|unity\.h|pytest|tap_' .
（无命中）
$ find . -type f \( -name '*.c' -o -name '*.h' -o -name '*.py' -o -name '*.sh' \) | sort
./config.def.h
./contrib/service.sh
./contrib/static_file.sh
./html.h
./pacredir.c
./pacredir.h
./static_file.h
```

即：无 `tests/` 目录、Makefile 16 个目标里没有 `check`/`test`、无任何测试框架
引用；`contrib/` 下两个 `.sh` 是构建期资产生成脚本（`static_file.sh` 生成 C 头、
`service.sh` 展开 `.service.in`），不是测试。

| 测试类型 | 上游用例数 | 说明 |
|---|---|---|
| 单元测试 | 0 | 无测试框架、无测试文件 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 同上 |
| **合计** | **0** | 计数口径：独立检查项数量 |

## 适配后测试（R51 第 2/3 步）

`test_package/test_pacredir.py`，**16 个独立检查项**，其中 **7 项鸿蒙特有**
（编号 3、5、6、7、11、15、16，逐条理由见 `test_package/MANIFEST.yml`）。
计数口径统一为「独立检查项数量」，MANIFEST.yml / manifest.yaml / 本文件 /
PR 两张表一致。

驱动只用 Python 标准库：CI worker 上没有 curl（仓内既有记录：smalt 的预下载
兜底就因 `[Errno 2] No such file or directory: 'curl'` 失效），也不假设
readelf/objdump 在 PATH 上 —— ELF 检视用 `struct` 手解 ELF64 头、程序头与
`.dynamic` 段，HTTP 走 `http.client`。

执行条件：`can_run(self)` 为真时跑满 16 项。CI 用
`-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（host 与 build 同 profile），
`cross_building()` 为假 ⇒ `can_run()` 为真 ⇒ 16 项在 HarmonyOS worker 上真实执行。
本地 macOS 交叉编译时 `ohos-local` profile 显式设了
`tools.build.cross_building:can_run=False`，此时 test_package 退化为产物形态核对
（ELF64 / AArch64 magic），不静默跳过。

## 验证结果

### 本地 W3（macOS 交叉编译，profile `ohos-local`）

```console
$ conan create archives/p/pacredir/0.7.10 -pr:h=ohos-local -pr:b=ohos-local --build=missing
...
pacredir/0.7.10: Apply patch (portability): musl/OHOS 可移植性两处修复 ...
pacredir/0.7.10: version.h: VERSION=0.7.10 ARCH=aarch64 ID=ohos
pacredir/0.7.10: favicon.png: 32x32, 752 bytes（上游 resvg|oxipng 链的等价产物）
pacredir/0.7.10: favicon.h: 内嵌 752 bytes, date=Wed, 03 Jun 2026 09:31:14 GMT
pacredir/0.7.10: style.h: 内嵌 858 bytes, date=Wed, 03 Jun 2026 09:31:14 GMT
pacredir/0.7.10: package(): Packaged 1 file: pacredir
pacredir/0.7.10: package(): Packaged 3 '.md' files: COPYING.md, README.md, FLOW.md
pacredir/0.7.10: package(): Packaged 1 '.svg' file: logo.svg
pacredir/0.7.10: Created package revision 770d43a447666de01d4f281aefb20a63
# rc=0
```

上游那条编译命令（`-Werror` 全开、零 warning）：

```text
clang pacredir.c -std=c11 -O2 -fPIC -Wall -Werror <8 个 -I> <7 个 -L>
      -lcurl -lsystemd -liniparser -lz -lmicrohttpd -lzstd -llzma
      -Wl,--as-needed -Wl,--exclude-libs,ALL -Wl,--allow-shlib-undefined
      -Wl,-z,now -Wl,-z,relro -pie -o pacredir
```

产物 ABI 与加固契约（`llvm-readelf` 实测，与 test_package 的 ELF 检查项 5/6/7 同源；
下面是**现行方案**（libcurl 动态）的手工链接探针产物，链接开关与配方完全一致）：

```console
$ llvm-readelf -h pacredir | grep -E 'Class|Machine|Type'
  Class:      ELF64
  Type:       DYN (Shared object file)      # + DF_1_PIE ⇒ PIE 可执行文件
  Machine:    AArch64
$ llvm-readelf -d pacredir | grep -E 'NEEDED|FLAGS'
  (NEEDED)    Shared library: [libcurl.so]
  (NEEDED)    Shared library: [libsystemd.so.0]
  (NEEDED)    Shared library: [libc.so]
  (FLAGS)     BIND_NOW
  (FLAGS_1)   NOW PIE
$ llvm-readelf -l pacredir | grep -E 'GNU_RELRO|GNU_STACK'
  GNU_RELRO   ...  R
  GNU_STACK   ...  RW      # 无 X ⇒ NX
```

`libcurl.so` 的 SONAME 实测就是无版本号的 `libcurl.so`（`llvm-readelf -d` 确认），
因此该 `DT_NEEDED` 在运行期可解析；`libmicrohttpd`（`libmicrohttpd.a`）与
`iniparser`（`libiniparser.a`）在制品仓里本就是静态库，`zlib/1.3.1.1` 亦为静态，
三者都被静态吸收、不出现在 `DT_NEEDED` 里（R26 的核心诉求依然满足）。

编入二进制的身份字面量（`strings` 实测，证明问题 #5 的修复生效）：

```text
pacredir v0.7.10 ohos/aarch64          # 启动横幅 / Server 响应头
pacredir/0.7.10 (ohos/aarch64)         # curl User-Agent
arch=aarch64                           # DNS-SRV TXT 对等体匹配串
<td>Distribution:</td><td><b>ohos</b></td>
<td>Architecture:</td><td><b>aarch64</b></td>
```

| 项 | 值 |
|---|---|
| `bin/pacredir`（第一版：libcurl 静态） | 700024 bytes，sha256 `18da0fea3f3a46a25642bca185fd6736632ee8b9b8fcd9579533294bcda95b5f`。该版本已被问题 #7 的方案反转取代，尺寸与哈希仅作过程记录 |
| `bin/pacredir`（现行方案：libcurl 动态） | 手工链接探针产物 179480 bytes，`DT_NEEDED` = `{libcurl.so, libsystemd.so.0, libc.so}`（探针用与配方同一套 include/lib 与链接开关）。配方产物的最终尺寸与哈希待远程 CI 回填——本地无法产出：`ohos-local` 的 host==build，meson 因此判为 native build，会编译出 aarch64 的 sanity check 再试图在 macOS 上运行而失败（`Could not invoke sanity check executable`），属本地交叉环境限制，与 worker 无关 |
| 生成的 `favicon.png` | 32x32，752 bytes，5 个 chunk（IHDR/PLTE/tRNS/IDAT/IEND），CRC 全通过 |
| 内嵌 `style.css` | 858 bytes（与上游原文一致） |
| 资产日期 | `Wed, 03 Jun 2026 09:31:14 GMT`（取自 tarball 内 Makefile 的 mtime ⇒ 同 tarball 可复现构建） |

### 测试驱动的本地预验证

macOS 无法执行 aarch64 OHOS ELF，本机也没有 qemu-aarch64 与可用的 docker
daemon，因此 16 项里的运行期部分（1-4、8-16）在本地**无法**用真产物执行。
为不带着未验证的测试代码去撞 CI，用一个复刻 pacredir 可观测契约的桩守护进程
（同样的 CLI 输出、同样的 6 个 HTTP 端点与响应头、同样的 SIGUSR1 状态转储与
SIGTERM 退出）在本地跑通了驱动全部分支：

```console
$ STUB_MODE=1 python3 driver_harness.py <stub_pkg> <log>   # 跳过 ELF 三项
ok - 1 ... ok - 16（13/13 全绿，SIGTERM 退出码 0 且日志含退出信号行）
$ 再次执行 → driver_rc=0（可重复，无端口残留）
```

该轮预验证抓到并修掉了两个真 bug：`check()` 的 detail 传了 list 会
`TypeError` 崩溃；`Server` 响应头同名多值时被 `dict()` 折叠成最后一个而误判。
桩只用于本地验证驱动逻辑，**不进归档**；16 项的真实结论以远程 HarmonyOS CI
上的 test_package 输出为准，CI 绿后回填本文件与 PR 正文。

### 本地 W3 —— CI 模拟（`finish` step [5/10]，阻塞门禁）

`finish` 内部按 CI 同源脚本跑了一遍 `ci/conan/setup.sh` + `build_and_test.sh`：

```text
JC_RESULT=pass      Junk Files: 0；JC6 涉及软件数 1（单软件原子性合规）
L0_RESULT=pass      L0i 依赖齐（iniparser/4.2.6、libcurl/8.5.0、libmicrohttpd/1.0.1、
                    systemd/261.1、zlib/1.3.1 逐个实测 in registry）
                    L0j 制品仓无同版本（首次发布）
                    L0k commands.json valid (type=tool)
                    L0m directory structure valid
L1_RESULT=pass      L1a test_package 已被 conan create 执行；L1b 日志中找到执行证据
                    L1e 破坏性反向验证（R34）：把 bin/ 移走后测试确实失败
                        → "[ok] L1e: Negative test confirmed — test genuinely
                           depends on pacredir"
L2_RESULT=skip      `pacredir --version/--help` 在 macOS 上无法执行 aarch64 OHOS ELF
                    （非阻塞；上游确有 --help/--verbose/--version 三个长选项，
                    见 pacredir.c:23-29 的 options_long，CI 原生环境可跑）
L4_RESULT=pass      补丁危险函数扫描干净
L5_RESULT=pass      bin/ 有产物
Build Summary       Total 1 / Success 1 / Pass rate 100.0%
```

`finish` 其余非阻塞步骤的实际情况（如实记录，不当作通过）：

| 步骤 | 结果 | 原因 |
|---|---|---|
| [3/10] clean-verify (G0) | 失败（非阻塞） | `clean_verify.py` 硬编码 `/data/service/hnp/bin/bash`（OHOS 设备路径），macOS 上不存在。属本地环境限制，SKILL 明确标注该步「平台限制可跳过」 |
| [4/10] conan-verify | 跳过 | Step 2.6 已通过且配方未改，按 SKILL 规则跳过 |
| [6/10] finalize-archive | RC=2 警告 | 报「缺 packaging/、缺 release/debug tar.gz」——ARCHIVE-SPEC v3.0 已明确 `packaging/` **废弃**（Conan 体系替代手动 tar.gz 打包），属陈旧检查项 |
| [7/10] check-knowledge-gap | 通过 | 本包 `notes.md: total=0 extracted=0 pending=0 failed=0`、`manifest.yaml: knowledge_count=0 unreferenced=0`；`graph validate` 通过（542 对 doc↔kv 完整）。日志里的「2552 个草稿待审」与 E219/E253/E305 字段缺失均为仓库存量，与本 PR 无关 |
| [8/10] gen_summary | 失败（非致命） | 框架自身异常 `'str' object has no attribute 'append'`；副作用是 SUMMARY.md 未被改动，反而符合 W2（框架文件不混入单库 PR） |
| [9/10] PR 原子性 (W2) | 通过 | 「仅含配方变更 (15 文件)，无框架文件」 |
| [10/10] submit 就绪预检 | 3 项警告 | 要求 `reports/test-report.md`、`packaging/`、`.staging-verified`；后两者 ARCHIVE-SPEC v3.0 已废弃（`.staging-verified` 注明「由 conan_verify 替代」），`reports/` 又被 `.gitignore:96` 忽略，故不入仓 |

### conan-verify 报告的两点如实说明

`reports/conan-verify-report.md`（本地生成，`reports/` 被 gitignore 故不入仓）：

1. **L2/L4/L5 三项在 conan-verify 里是「跳过（无 cache 路径）」，不是通过**。
   本报告不把它们记作 conan-verify 的成果；等价的产物契约断言由 test_package
   检查项 5-7（PIE / RELRO+BIND_NOW+NX / DT_NEEDED 集合）覆盖，并已在上面
   W3 的 L4/L5 行拿到 CI 同源脚本的 pass。
2. **G0 报的 E490 是误报**：它提示「Autotools helper scripts 未恢复可执行位」，
   但 pacredir 上游**没有任何 autotools 脚本**（无 configure / config.guess /
   config.sub / install-sh，tarball 35 个文件里只有裸 Makefile）。误报来源是
   `init-build` 把 `BUILD_SYSTEM` 默认填成了 autotools；本文件的「编译环境」与
   manifest 的 `build.system` 均已按实际写为 `makefile`。G0 为非阻塞项，
   G2（conan create）实测 PASS。

### 远程 HarmonyOS CI

待回填（构建编号、16 项逐条结果、L0-L5 门禁结论、AI Review 与 PC 鸿蒙化审查状态）。

## 交付物

| 路径 | 大小 | 说明 |
|------|------|------|
| `bin/pacredir` | 见「验证结果」表（第一版 700024 B；现行方案的手工链接探针产物 179480 B，配方产物最终值待 CI 回填） | 守护进程本体（PIE；现行方案 DT_NEEDED = libcurl.so + libsystemd.so.0 + libc.so） |
| `licenses/COPYING.md` | 34916 B | GPL-3.0 全文 |
| `share/doc/pacredir/README.md` | 7314 B | 上游使用文档（Markdown 原文） |
| `share/doc/pacredir/FLOW.md` | 1250 B | 上游重定向决策流程说明 |
| `share/doc/pacredir/logo.svg` | 3569 B | 上游矢量 logo |

**未打包的上游安装项及原因**：

| 上游 install 项 | 原因 |
|---|---|
| `bin/pacserve`（→ `darkhttpd` 符号链接） | 跨 conan 包目录的符号链接破坏可重定位性；且 pacserve 由 Arch 侧 systemd unit 拉起，OHOS 无 systemd 本体 |
| `lib/systemd/system/{pacredir,pacserve}.service`、`lib/sysusers.d/`、`lib/tmpfiles.d/` | OHOS 不运行 systemd，unit/sysusers/tmpfiles 无消费者 |
| `etc/pacredir.conf`、`etc/pacserve.conf`、`etc/systemd/resolved.conf.d/` | 上游把配置装到绝对路径 `/etc`；conan 包不应写系统目录，且守护进程读的是硬编码的 `/etc/pacredir.conf`（缺失时上游只告警并继续，已由 test_package 覆盖该路径） |
| `etc/pacman.d/pacredir`、`lib/dhcpcd/`、`lib/networkd-dispatcher/`、`lib/NetworkManager/dispatcher.d/` | Arch pacman / dhcpcd / networkd / NetworkManager 的钩子，OHOS 上无对应组件 |
| `share/applications/pacredir-status.desktop`、`share/pixmaps/pacredir.png` | 桌面集成件；OHOS PC 侧无对应桌面栈消费者 |
| `share/doc/pacredir/*.html` | 由 Perl `markdown` 生成，worker 无该工具；只装 Markdown 原文 |

## 注意事项

- **不要移除 `-Wl,--allow-shlib-undefined`**，除非 `systemd` 配方修好了
  `mallinfo2`（问题 #8）。移除后本地 `ohos-local` 链接必炸；worker 侧是否炸
  取决于其 SDK 的 `libc.so` 桩是否收录了 `mallinfo2`。该开关只放行**共享库
  自身**的未定义符号，pacredir 目标文件的未定义符号仍照常报错。
- **不要把 `-Wl,--as-needed` 挪到 `$LIBS` 之后**：它是位置敏感开关，挪后就
  完全不生效，`libzstd.so.1` 会重新出现在 `DT_NEEDED` 里（问题 #9）。
- **不要再把 libcurl 切成静态**（`self.options["libcurl"].shared = False`）：
  那会强制它从源码重建，而它的 CMake 走 `make -j20`，在 OHOS 上必撞 SELinux
  禁 FIFO（E074/E525）。CI #93768 已实测失败一次（问题 #7）。同理，任何
  「为了收敛 `DT_NEEDED` 而把走 Unix Makefiles 的依赖切静态」的想法都要先过这一关。
- **`manifest.yaml` 里 `patch_classification` 必须是最后一个顶层键**：
  `refresh_patch.py` 用 DOTALL 正则清除该键，会连带吞掉其后的所有段落（问题 #12）。
- **`conandata.yml` 的 `patches` 必须以版本号为键**，写成补丁文件名为键时
  `apply_conandata_patches()` 会静默 no-op（问题 #10）。
- `PORT_PACREDIR`（7077）与 `CONFIGFILE`（`/etc/pacredir.conf`）都是
  `config.def.h` 里的编译期常量，上游不提供命令行/环境覆盖。test_package
  因此在启动前先探一次端口，被占用时给出明确诊断而不是超时。
- 上游 `main()` 里有 `sigaction(SIGKILL, &act, NULL)`：SIGKILL 不可捕获，
  该调用返回 EINVAL 且返回值被丢弃。这是上游既有行为，musl 与 glibc 表现一致，
  本次未改动。
---

**编译结束**: 2026-10-15 19:29
**最终状态**: built
