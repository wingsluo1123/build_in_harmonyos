# gammastep 2.0.9 适配笔记

> 上游：https://gitlab.com/chinstrap/gammastep （redshift 的活跃分支，色温调节 CLI）
> 本件是本 PR 的**技术真相面**：PR 正文（白名单 H2）只放模板要求的内容，细节与读数全在这里。

## 编译环境

- 构建系统：autotools（**git tag archive，不含 `configure`/`Makefile.in`/`m4/` ⇒ build() 先 `autoreconf -fi`**）
- 编译器：clang 15.0.4（OHOS 适配版 conan profile `ohos-aarch64`：os=OHOS / arch=armv8 / Release）
- 目标：HarmonyOS PC aarch64
- 主机：`nproc=8`（/proc/cpuinfo 20 核，本 shell 亲和掩码后 8）· MemAvailable 实测 6.7–8.3 GB
- 日期：2026-10-16
- 构建占用（v3.1 槽位声明用）：`memcap-run.py --probe` 三轮实测**峰值 131 / 139 / 142 MB**
  ⇒ 槽位声明 `--mem 400`（约 2.8× 余量），作业预算由闸导出 `-c tools.build:jobs=$BUILD_SLOT_JOBS`
- 最终状态：**`conan create` rc=0，`test_package` 9/9 PASS**

## 依赖

configure.ac 的 4 个可选调节后端 + i18n 工具链，全部取 ohpcd 已发布 OHOS armv8 二进制：

| 依赖 | 版本 | 用途 | 声明位置 |
|---|---|---|---|
| wayland | 1.24.0 | Wayland 后端（`wayland-client ≥1.15.0` + `wayland-scanner`） | requires |
| libdrm | 2.4.133 | DRM 后端（`libdrm`） | requires |
| libxcb | 1.16 | RANDR 后端（组件 `.pc` = `xcb` + `xcb-randr`） | requires |
| xorgproto | 2025.1 | 直接 include 的 X 头（`<X11/Xlib.h>` 链） | requires |
| libx11 | 6.4.0 | VidMode 后端（`x11`） | requires |
| libxxf86vm | 1.1.5 | VidMode 后端（`xxf86vm`） | requires |
| gettext | 0.22.5.1 | `AM_GNU_GETTEXT([external])` 的 **libintl**（musl 无内建 gettext） | requires |
| automake / libtool / intltool / gettext | 1.18 / 2.5.4.1 / 0.51.0 / 0.22.5.1 | bootstrap 工具链（见问题表 2） | build_requires |

**⚠ X11 世代必须整条同源（本包首错）**：本仓存在两条互斥的 X11 世代 ——
`libx11/1.8.13.x` 钉 `libxcb/1.17.0.x + libxau/1.0.12`，
`libx11/6.4.0` 钉 `libxcb/1.16 + libxau/1.0.11`；而 `libxxf86vm/1.1.5` 钉 `libx11/6.4.0 + libxext/6.4.0`。
混用直接 `ERROR: Version conflict: Conflict between libxau/1.0.11 and libxau/1.0.12 in the graph`
（`Conflict originates from libx11/1.8.13`）⇒ 整条栈按同域先例 `archives/x/xgamma/1.0.8` 取 6.4.0 世代。
（`libxau` / `libxdmcp` / `xtrans` 由该栈传递引入，未显式声明。）

## 编译步骤

```bash
export CONAN_HOME=~/tmp/ch/home-gammastep     # 三步播种：拷 remotes.json + 追加 download_cache + conan remote list 见 ohpcd
conan create archives/g/gammastep/2.0.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=$BUILD_SLOT_JOBS
```

配方内部顺序（`conanfile.py`）：

1. `source()`：官方 tag archive + **wayland 源码**（静态重建 scanner 用，`scanner_sources`）
2. `generate()`：收窄 wayland 的 `cpp_info.libs` → `PkgConfigDeps` → `VirtualBuildEnv` →
   `AutotoolsToolchain`（`--enable-drm/wayland/randr/vidmode`、`--disable-geoclue2/gui`、
   显式等值 `--build/--host=aarch64-linux`）→ 注入 `ACLOCAL_PATH` / `gettext_datadir` / libintl `-I -L -lintl`
   → 自编译 scanner 的 `.pc` 顶到 `PKG_CONFIG_PATH` → **任务局部 libtool shadow** 并把 shadow 前插到 `LDFLAGS`
3. `build()`：**静态重建 `wayland-scanner`** → `autoreconf -fi`（intltoolize prefix shim）→
   对生成的 `configure` 打两处幂等补丁 → `configure` → `make -j1`
4. `package()`：`make install` + COPYING
5. `test()`：`test_package/test.sh`（9 条消费者断言，见「测试口径」）

configure 摘要（`configure` 尾部自印，四个后端全部 `yes`）：

```
    Adjustment methods:
    DRM:        yes
    Wayland:    yes
    RANDR:      yes
    VidMode:    yes
    Location providers:
    Geoclue2:   no
    GUI:        no
```

## 遇到的问题与解决方案

| # | 问题（首错原文） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `ERROR: Version conflict: Conflict between libxau/1.0.11 and libxau/1.0.12 in the graph. Conflict originates from libx11/1.8.13` | 两条 X11 世代混用（见「依赖」） | 整条栈取 `libx11/6.4.0 + libxcb/1.16 + libxau/1.0.11` 世代（xgamma 同款） |
| 2 | 上游 git archive **无 `configure`**；`AC_PROG_INTLTOOL([0.50])` + `AM_GNU_GETTEXT([external])` 要 m4/intltoolize/autopoint | tag archive 故意不带生成件；而设备自带 aclocal 是 1.17 driver + 1.16 share dir（`Can't locate Automake/Config.pm`） | `build_requires`: automake 1.18 + libtool + intltool + gettext；`autoreconf -fi`；`ACLOCAL_PATH` 收全图 m4 目录 |
| 3 | `intltoolize: cannot copy …`（conan intltool 包把 `prefix=/` 烧进脚本） | 脚本按烧死 prefix 去找 `//share/intltool/Makefile.in.in` | 复制 `intltoolize` 到 build 内 `toolshim/` 并改写那一个常量，PATH 前置（l3afpad/ddccontrol 同款 shim） |
| 4 | `autopoint: infrastructure files for version 0.18.1 not found` | conan gettext 包把 `prefix="/"` 烧进 autopoint 且把 relocation 分支编掉 | 导出 `gettext_datadir=<gettext 包>/share/gettext`（脚本留了 `: ${gettext_datadir=…}` 入口） |
| 5 | `can't create ./confXXXXXX/subs1.awk: Permission denied` | `configure` 里 `(umask 077 && mktemp -d ./confXXXXXX)` 在 setgid 的 hmdfs 卷上建出创建者自己也写不进的目录（E110/E112） | 对**生成的** `configure` 幂等替换 `umask 077` → `022` |
| 6 | intltool.m4 的 `XML::Parser` 探测必失败（设备 perl 无该模块） | 无显示/无 GUI 构建下树内**零 xml.in 消费者**，探测无意义 | 反转 intltool.m4 官方 off-switch（`if test "x" != "xno-xml"` → `=`）；同 klavaro/3.14 patch0001 |
| 7 | **libtool 最终链接**：`libtool: error: cannot find the library '//lib/libxcb.la' or unhandled argument '//lib/libxcb.la'`（伴随 `library '…/libxcb-randr.la' was moved`） | 制品仓 `.la` 元数据里留了**构建机**的 stale 路径：`libxcb-randr.la` 的 `dependency_libs` 含 `//lib/libxcb.la` 与 `/…/.conan2/p/…/libXau.la`，`libdir` 也指向别处的 `.conan2` 缓存。实测 **30 份 `.la`** 中招（25 份 libxcb 家族 + 4 份 gettext + libXau/libXdmcp 的 libdir）；libtool 会**递归**打开每个 `.la` | **任务局部 libtool 递归 shadow**（`archives/l/libxfixes/6.0.2` 的 E522 实现同款）：把依赖 `.la` 及其声明的库产物拷进 build 内 `libtool-shadow/`，重写整条 `dependency_libs` 闭包 + `libdir`，并把 shadow 放到 `-L` 最前。⛔ 不就地改依赖包（污染别的构建），⛔ 不只修直接那一层；对已死不存在的 `.la` 引用（gettext 的 `//lib/libintl.la`）逐条记录后丢弃 |
| 8 | `Error loading shared library libwayland-cursor.so.0: Permission denied`（gammastep **任何**子命令 rc=127，连 `-V` 都跑不了） | `PkgConfigDeps` 把 wayland 包的 `cpp_info.libs = ["wayland-client","wayland-server","wayland-cursor"]` **全部**写进生成的 `wayland-client.pc` 的 `Libs:` 行 ⇒ configure 的 `PKG_CHECK_MODULES([WAYLAND], …)` 让 gammastep 白链 server/cursor；而本机实测 `libwayland-cursor.so.0.24.0` 的 `.codesign` 在本设备校验不过 ⇒ dlopen EACCES（同目录 `libwayland-client.so.0` 正常；把 cursor 复制后 `binary-sign-tool -selfSign 1` 重签即可 dlopen OK ⇒ 坐实是签名面） | 消费方把该 dep 的 `cpp_info.libs` 收窄为 `["wayland-client"]`（gammastep 源码 `grep -rn cursor src/*.c` = **0**，真实依赖面只要 client）⇒ 不再链 cursor。**不改制品仓、不重签依赖、不改上游** |

## 源码修改

**零补丁**（`patches/` 为空，`apply_conandata_patches(self)` 保留调用以满足 G1 完整性）。
问题表 5/6 的两处是打在 **autoreconf 生成的构建产物** `configure` 上，不回写上游源码树。

## 构建期能力墙（B 证据）：制品仓 `wayland-scanner` 在本机不可执行

`configure.ac` 用 `PKG_CHECK_VAR(WAYLAND_SCANNER, wayland-scanner, wayland_scanner)` 取制品仓
`wayland` 包的 `bin/wayland-scanner`，`src/Makefile.am` 用它生成 `gamma-control-protocol.c` /
`orbital-authorizer-protocol.c`。本机一手实测（逐条读数，命令与输出同序）：

```
[1] file(1):  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
[2] 未签名执行: Operation not permitted                                      rc=126
[3] 复制到 ~/tmp 再跑（排除所在卷 noexec）: Operation not permitted            rc=126
[4] 对照 clang 现场编译的二进制                                               rc=0
[5] binary-sign-tool sign -inFile … -outFile … -selfSign 1
      → INFO add codesign section success / write code sign data success
    ./ws.signed --version →
      Error loading shared library /storage/Users/currentUser/.cache/conan2/p/expat9fb72708ad085/p/lib/libexpat.so
      Error relocating ./ws.signed: xmlNewValidCtxt: symbol not found
[6] LD_LIBRARY_PATH=<同 home 内 expat/libxml2 真实 libdir> 后仍报**同一条绝对路径**
[7] ls -d /storage/Users/currentUser/.cache/conan2 → No such file or directory
[8] 同 home 内 expat 包 libdir 确实有 libexpat.so ⇒ 不是"库没下载"，而是 NEEDED 写死了别的绝对路径
```

⇒ ①未签名 → EPERM；②自签后 → `DT_NEEDED` 里是**构建机缓存的绝对路径**（不是 soname），
`LD_LIBRARY_PATH` 无处插入 ⇒ 该工具在本机**没有可用执行路径**。
**处方**：从上游同版本 wayland 源码**静态重建** scanner（只编 `scanner.c` + `wayland-util.c`，
第三方依赖取宿主 SDK 的 `libexpat.a`），写 `wayland-scanner.pc` 顶到 `PKG_CONFIG_PATH` 最前。
构建日志实证生效：`GEN gamma-control-protocol.c` / `GEN orbital-authorizer-protocol.c` 正常产出。
（本题沉淀为 `knowledge/drafts/DRAFT-gammastep-2.0.9-wayland-scanner-exec-denied-static-rebuild.{kv,md}`，
关联 Issue 见 PR 正文 3+2 行。）

## 能力面披露（运行期 · 实测 · 逐项）

gammastep 是**改显示器 gamma 的硬件相关工具**：四个后端在本机**全部编译通过、但运行期一个也用不了**。

| 后端 | 编译 | 运行期 | 依据 |
|---|---|---|---|
| DRM | ✅ `--enable-drm` configure=yes | ❌ 不可用 | `/dev/dri` **ENOENT**（同夜 ddccontrol 亦实测 ENOENT） |
| Wayland | ✅ `--enable-wayland` configure=yes | ❌ 不可用 | 无 Wayland compositor（无可达合成器） |
| RANDR | ✅ `--enable-randr` configure=yes | ❌ 不可用 | 无 X 服务器（X11 socket 不可达） |
| VidMode | ✅ `--enable-vidmode` configure=yes | ❌ 不可用 | 无 X 服务器 |

⇒ 交付形态按 `appres` / `ddccontrol` 先例：**编译照常交付 + `test_package` 只断言参数解析阶段的文本/查询路径 +
本件如实披露「运行期核心功能不可用及逐条原因」**，⛔ 不谎称能改色温、⛔ 不 mock 设备节点、⛔ 测试不碰真设备。
`-m list` 那几条断言不是"跑不起来就算了"的凑数：方法表由编译期 `gamma_methods[]` 数组生成，
**它是"四个 `--enable-*` 真的生效、四个后端真的编进去了"的机器可读证明**。

## 测试口径（三处同源：本件 / `test_package/MANIFEST.yml` / PR 正文两表）

- **上游**：`0`（四口径实测：`test*` 目录 0、`TESTS =`/`check_PROGRAMS =` 0、`res/` 0、`*RUNTEST*` 0、
  `examples|demo/*.c` 0、`*.sh` 0、源码 `assert(` 0、configure 无测试宏）
  ⇒ `make check` 是 automake 空转，**不声称跑过不存在的上游套件**。
- **适配后**：`test_package/test.sh` **9 条断言 / 1 个消费者程序**（`gammastep` 二进制行为断言）：

  1. `-V` → rc=0 且 stdout **精确等于** `gammastep 2.0.9`
  2. `-h` → rc=0 且含 `Usage: gammastep`
  3. `-m list` → rc=0 且含 `Available adjustment methods:`
  4–7. `-m list` **逐条**列出 `drm` / `wayland` / `randr` / `vidmode`（编译期后端证明）
  8. `-m list` 列出恒建的 `dummy`
  9. `-m nosuchmethod` → rc=1 且 stderr 含 `Unknown adjustment method`

  全部在参数解析阶段 `exit()`，**不打开任何设备节点、不连显示服务**。
- 两表口径差异：上游按 §12.72 **资产口径** = 0；适配后按**可执行断言口径** = 9（消费者测试行）。

## 路径 B 查重读数（四范围 · 2026-10-16 实测）

- `knowledge/graph/index.tsv` + `E*.kv`：`wayland-scanner` **0**、`drm` **0**、`gamma` **0**；
  同族命中 `E522`（libtool 递归 shadow —— 本包**复用**其处方）、`E527`（构建期 native 工具包装，但那条是
  **Python 脚本改 shebang**）、`E463`/`E472`（制品仓工具自签 —— 停在"签了就可用"）。
- `knowledge/drafts/`：`DRAFT-ohos-static-tool-bypass-dlopen-limit.{kv,md}` 同机制族，但其症状**只有
  dlopen 失败一种**，未记「未签名 ⇒ EPERM」与「NEEDED 绝对路径」；`DRAFT-PKG-VER-remote-prebuilt-so-codesign-is-device-bound`
  （`经验文档/B草稿库/`）覆盖问题表 8 的 codesign 面 —— 本包**复用**。
- `经验文档/经验库/` 全量：`wayland-scanner` / `静态编译` / `静态重建` **0 命中**。
- 同**域**先例（非同一机制）：`archives/x/xgamma/1.0.8`（X11 gamma CLI）覆盖的是**运行期**无 X server
  的能力面；本包运行期那一半同样复用它的交付模式，构建期工具执行那一半是新增量。
- 同源重复自查：`archives/` 全树 `grep -rn "gammastep\|chinstrap\|redshift"` **0 命中**；
  平台全表（10869 条）扫 `gamma` 仅命中无关 `kgamma` ⇒ 无同源同版本重复。

## W4 独立审计后的两点补充说明（2026-10-16，仅文档、无代码变化）

### ① 静态 wayland-scanner 用的 expat 版本偏差（审计 P2-2）

静态重建的 scanner 实际链接的是**宿主 SDK 的 expat 2.7.3**
（`/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`，路径在配方里是显式回退项），
而同图声明的依赖是 **`expat/2.8.2`**（它是 `wayland` 包的传递依赖，`libexpat.so` 随图安装）。

**为什么回落**：本机实测 ohpcd 的 `expat/2.8.2` 包只装动态库 ——
`p/lib/` 下只有 `libexpat.so`（+ `.so.*`）与 `cmake/`、`pkgconfig/`，**没有 `libexpat.a`**；
而静态链接 scanner 必须要有 `.a`，故只能取宿主 SDK 那一份。

**边界（为什么这不构成目标侧 ABI 混装）**：scanner 是**构建期工具**，只在构建机上运行、
**不进目标包**；它链接的 expat 属**构建机库**，与目标包里 `wayland → expat/2.8.2` 的运行期
依赖链互不相干（目标二进制 `bin/gammastep` 的 `NEEDED` 里是 `libexpat.so`，由 conan 图提供）。

**先例**：同一条 SDK 静态库路径在仓内另有 **9 份**配方使用（含本包；`grep -rl
"hnp/expat.org" archives/*/*/*/conanfile.py` 实测 = 9 —— 注：这是本次实测值，
不是"17 份"，以实测为准）。

### ② 为什么 configure 的两处改写不能走 `patches/`（审计 P2-3）

问题表 5/6 的两处改写（`umask 077` → `022`、intltool 的 XML::Parser 探测反转）**无法写成补丁**，
理由是**补丁没有落点**：本包源码是上游 **git tag archive**，树内**根本没有 `configure`**
（也没有 `Makefile.in` / `m4/`）；`configure` 是 `build()` 里 `autoreconf -fi` **当场生成**的。
`patches/` 的补丁在 `apply_conandata_patches(self)` 阶段作用于**源码树既有文件**，
那时 `configure` 尚不存在 ⇒ 补丁必然 `can't find file to patch`。

⇒ 本包的处置是：在两处改写点**紧跟 `autoreconf` 之后**就地幂等改写生成的 `configure`
（替换计数打印进日志；`umask 077` 不存在则跳过；XML 守卫若两种形态都找不到则**直接 raise**，
不静默继续 configure）。这三条合起来保证"要么改对、要么当场失败"，不会产出假绿。

⇒ 因此本包 `patches: {}` 为空、`patches_applied: []`，但 `apply_conandata_patches(self)` 仍保留调用
（G1 完整性要求）；**上游源码树零改动**这一点不受影响。

## 验证结果

```
# W0 preflight（rc=0）
bash ci/scripts/preflight_check.sh gammastep/2.0.9
[OK] 预检通过（无依赖需要检查）        # 首配、conanfile 尚未生成时属正常

# recipe-search（rc=0）
python3 scripts/ohc-run.py recipe-search gammastep
⚠️ 无相似配方（语料 9338 条）—— 首稿走 conan-init 模板

# 构建（conan create，过 build-slot 闸 --mem 400，memcap-run --probe）
... CCLD     gammastep
--- gammastep 2.0.9 consumer verification ---
PASS 1: -V -> rc=0 and exact 'gammastep 2.0.9'
PASS 2: -h -> rc=0 and usage line present
PASS 3: -m list -> rc=0 and method-list header present
PASS 4: -m list names backend 'drm'
PASS 5: -m list names backend 'wayland'
PASS 6: -m list names backend 'randr'
PASS 7: -m list names backend 'vidmode'
PASS 8: -m list names always-built backend 'dummy'
PASS 9: -m nosuchmethod -> rc=1 and 'Unknown adjustment method' on stderr
test gammastep 2.0.9: 9/9 checks PASS
MEMCAP[probe] peak=139MB budget=0MB rc=0 用时184.8s
INNER_RC=0

# 上游 make check：注册用例 = 0（automake 空转），见「测试口径」
```

## 注意事项

- 问题表 7 的 shadow 是**消费方**动作：只写 build 内目录，**不动制品仓、不动他人归档**。
  shadow 自检会对 sanitized `.la` 的依赖做存在性断言（"把坏元数据搬家"会当场 raise）。
- 问题表 8 的 codesign 面（`libwayland-cursor.so.0` EACCES）是**平台侧**现象，本包以"收窄真实依赖面"绕开；
  若未来有包**真的需要** cursor/server，就得走"给依赖 .so 重签"那条路（另有草稿在池）。
- 运行期四个后端全不可用是**平台能力缺口**，不是本包缺陷；本 PR 不据此宣称"色温可调"。

**编译结束**: 2026-10-16
**最终状态**: built
---

**编译结束**: 2026-10-16 19:31
**最终状态**: built
