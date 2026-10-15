# exfatprogs 1.4.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（OHOS SDK，aarch64）、GNU Make 4.4.1、conan 2.29.1、autoconf 2.72
- 状态: built

## 源码获取（R39 端点级实测，2026-10-15）

- **主源 = 上游官方 release 直链**：
  `https://github.com/exfatprogs/exfatprogs/releases/download/1.4.3/exfatprogs-1.4.3.tar.xz`
  - 实测 HTTP **200**、**425988** 字节、sha256
    `57226a8ec1bfbce06d68a42cde8cd980414a9457882e691fbce4a4f86c8d5f08`
  - 首次连接失败（curl 28 connect timeout）、第二次 200 ⇒ 属抖动，非不可达
- **哈希交叉核对（只作核对，不作源）**：
  `http://deb.debian.org/debian/pool/main/e/exfatprogs/exfatprogs_1.4.3.orig.tar.xz`
  HTTP 200 / 425988 字节 / 同 sha256，与 `exfatprogs_1.4.3.orig.tar.xz` **逐字节相同**，
  且与 `exfatprogs_1.4.3-1.dsc` 的 `Checksums-Sha256` 行逐字一致。
  ⇒ conandata.yml 采用上游 HTTPS 标量，**不加镜像前缀、不用 Debian 池址作源**。
- 已验证 tarball 按 sha256 预置到共享 `core.sources:download_cache`，
  sidecar 同时登记官方 URL 与 E017 注入的 ghfast URL（否则缓存被判 dirty，
  首次 G2 就是这样被 ghfast 读超时打断的）。

## 编译步骤

1. `preflight_check.sh exfatprogs/1.4.3` → RC=0（首跑时尚无 conanfile，
   生成配方后以 `conan install --build=never` 精确复核依赖）。
2. `recipe-search exfatprogs` → 语料 9001 条无相似配方，首稿按 dosfstools 4.2
   （同族 FS 工具、同 autotools、同 application 型）定稿。
3. 框架裸构建 Step3–Step8：
   `sh <src>/configure --prefix=$HOME/usr/local --build=aarch64-unknown-linux-gnu
   --enable-tests CC=clang CXX=clang++ CPPFLAGS=-I<libblkid>/include/blkid`
   → `make` → `make install DESTDIR=<staging>`。
4. conan 配方（`conan-verify` G2 = `conan create`）：
   configure 同上（`--prefix=/` 由 AutotoolsToolchain 给出，`--bindir/--sbindir`
   收到 `${prefix}/bin`）→ `make -j1` → `make -j1 check` →
   **上游 `lib/tests/suite0000-bitmap`** → **上游 `tests/test_fsck.sh`（23 例）** →
   `make -j1 install DESTDIR=<package_folder>` → test_package（8 条断言）。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `failed to get kernel version.` / `failed to open <img>. -1`，rc=8；上游套件 `Passed 0 of 23` | `uname().release` = `HongMeng Kernel 1.12.0`，`exfat_cmp_kernel_ver()` 用 `sscanf("%hu.%hu.%hu")` 从**头部**取号必然失败；**且第二层**：即便解析成功，`1.12.0 < MIN_KERNEL_VER {2,6,0}` 仍会以 `pre-2.6` 拒绝 | 补丁 `patches/0001-…`：release 首字符非数字 ⇒ 视为"版本不可评估"直接放行；一处同时关掉两层，不改闸值、不注入平台宏（见 `knowledge/drafts/DRAFT-exfatprogs-1.4.3-non-numeric-uname-release-kernel-gate`） |
| 2 | `configure: error: could not make ./config.status`（`ac_delim_n=130` vs `ac_subst_vars=132`） | 用带中文的 CONAN_HOME 时，conan 生成的 `blkid.pc` prefix 带非 ASCII，`BLKID_CFLAGS/BLKID_LIBS` 进入 `ac_subst_vars`，toybox sed 对含非 ASCII 字节的行**整行匹配失败** ⇒ 分隔符循环 6 轮都数不齐 | CONAN_HOME 改用纯 ASCII 标识（`home-exfatprogs143`）；**配方侧无需改动**（CI 的 conan home 本就 ASCII） |
| 3 | `configure: error: could not make ./config.status`（`could not make ./config.status`，首错） | HMDFS 上 `(umask 077 && mktemp -d ./confXXXXXX)` 生成 `drwx--S---`，属主也写不进（E011/E114） | 配方内 `replace_in_file` 把 configure 的 `(umask 077 && mktemp/mkdir` 放宽为 `022`（保留真实临时目录创建） |
| 4 | `checking for blkid >= 2.20... yes` 后 `mkfs/mkfs.c:26:10: fatal error: 'blkid.h' file not found` | 上游 util-linux `blkid.pc` 是 `Cflags: -I${includedir}/blkid`，conan `PkgConfigDeps` 按 `cpp_info.includedirs` 生成的是 `Cflags: -I${includedir}` ⇒ 少了组件子目录；configure 只查"包存在"，编译期才暴露 | 配方把 `-I<libblkid package>/include/blkid` 追加进 `CPPFLAGS` |
| 5 | `Package blkid was not found in the pkg-config search path` | conan 的 `PkgConfigDeps` 写出 `.pc` 但不把 generators 目录加进 `PKG_CONFIG_PATH`（E468） | `generate()` 里 `self.buildenv_info.append_path('PKG_CONFIG_PATH', self.generators_folder)`（E468 推荐方案原样） |
| 6 | `make: jobserver mkfifo: … Operation not permitted` | 并行 jobserver 的 fifo 在 HMDFS 上建不了（R9/E074） | 全程 `make -j1` |
| 7 | `configure: error: working directory cannot be determined` 风险（E386） | host profile `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 指到设备 hnp bash | 每条 configure/make/install/test 以 `env -u CONFIG_SHELL SHELL=/bin/sh sh -c …` 执行 |
| 8 | `xxd: Max 1 argument (see "xxd --help")` → 上游 4 个 upcase 用例 ERROR | 设备 toybox xxd 只收 1 个参数，上游调用是 vim 语义 `xxd -r - <image>`（stdin 十六进制 + 按地址就地打补丁） | `tool_requires("xxd/9.1.0")`（制品仓已发布、`--build=never` 实测二进制可取），**不写 shim、不改上游脚本** |
| 9 | `env: 'cd': No such file or directory`（exit 127） | `_pin` 的 `env …` 前缀后面直接跟 `cd X && Y`，`env` 把 `cd` 当要执行的程序 | `_pin` 改为 `env … sh -c '<整条命令>'` |
| 10 | G2 首跑 `Error downloading file https://ghfast.top/…: Read timed out` | E017 预防把 URL 临时注入 ghfast，而下载缓存 sidecar 只登记了官方 URL ⇒ 缓存被判 dirty、清空重下 | sidecar 同时登记官方 URL 与 ghfast URL + 删 `.dirty` 后重跑（§12.39 口径） |
| 11 | `ModuleNotFoundError: No module named 'conan.tools.pkgconfig'` | conan 2.29 里 `PkgConfigDeps` 在 `conan.tools.gnu` | `from conan.tools.gnu import PkgConfigDeps` |

## 源码修改

**唯一一处补丁**：`patches/0001-lib-exfat-skip-kernel-version-gate-for-non-numeric-release.patch`
（+14 行，`strip: 1`，只改 `lib/libexfat.c` 的 `exfat_cmp_kernel_ver()`）：

```c
+	if (uts.release[0] < '0' || uts.release[0] > '9')
+		return 0;
```

判据是**字符串形状**不是平台宏 —— Linux release（`6.6.0-…`）仍走原两层判定，
行为逐字节不变；`patches/` 里不含任何 `__OHOS__`（PF5）。

其余 **7 处适配全部落在配方与构建环境层**（E011 umask、E386 shell 路由、E468
PKG_CONFIG_PATH、CPPFLAGS 组件子目录、`--build` 三元组、串行 make、xxd
tool_requires），**上游源码、测试脚本、Makefile 一律未改**。

## 依赖版本

| 角色 | 引用 | 解析方式 |
|---|---|---|
| 运行/构建依赖 | `libblkid/2.42.2` | `conan install . --build=never` → RC=0，**二进制从 ohpcd 下载成功**（⛔ 未用通配 `conan list`） |
| 构建期工具 | `xxd/9.1.0` | 同上，RC=0，二进制下载成功 |
| 系统 | clang 15.0.4 / GNU Make 4.4.1 / autoconf 2.72 / pkg-config 0.29.2 | 设备自带 |

`fts.h` 不存在 ⇒ 上游 `dosattr` 子目录按 `AM_CONDITIONAL` 自动不构建（上游自带分支，非本方裁剪）。

## 验证结果

```bash
# 上游测试（conan create 内 build() 真实执行，2026-10-15）
#   tests/test_fsck.sh            : Passed 23 of 23, rc=0
#   lib/tests/suite0000-bitmap    : rc=0（5 个测试函数）
#   make -j1 check                : 上游未注册任何 automake TESTS（结构性空跑，如实记录）
# 五维账本：上游静态 28 / 实际执行 28 / 通过 28 / skipped 0 / 失败 0
# 消费者测试（test_package/test_exfatprogs.py）
CONSUMER ASSERTIONS: 8/8 passed
# 配方门禁 conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS（2026-10-15 VERIFY_RC=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/mkfs.exfat` `bin/fsck.exfat` `bin/tune.exfat` `bin/exfatlabel` `bin/dump.exfat` `bin/exfat2img` | 上游 `sbin_PROGRAMS`（AutotoolsToolchain 把 `--sbindir` 收到 `${prefix}/bin`） |
| `bin/exfat-uctbl2bin.sh`、`share/doc/exfatprogs/*.txt`、`share/man/man8/*.8` | 上游 `dist_libexec_SCRIPTS` / `dist_upcase_bin_DATA` / `dist_man8_MANS` |
| `licenses/COPYING` | GPL-2.0-or-later |

## 能力面（如实记录）

- **可用面**：`mkfs.exfat` / `fsck.exfat` / `dump.exfat` / `exfatlabel` 在**普通文件镜像**
  （`S_ISREG` 路径）上完整可用，非特权即可 —— 上游只在 `fstat()` 判定 `S_ISBLK`
  之后才碰 `/sys/dev/block`，文件镜像不经过那段代码。
- **不可用面**：块设备与挂载面（`/dev/loop*`、`losetup`、`mount`）对非特权用户不可用
  （实测 `/sys/dev/block` 读取 `Permission denied`）。**不属本交付断言面**，
  如实记录、不写成可用。

## 注意事项

- 框架 `build` 驱动 Step5（staging 安装）在本机两次被外部终止（日志停在
  Step5 头、无 HANDOFF），Step3/Step4 已实测全绿；本包的安装验证改由
  `conan-verify` G2（`conan create`）承担，其内部走完整 configure→make→
  check→上游两套件→install→test_package，证据见 `reports/conan-create.log`。
- 框架 Step3 的工具巡检会自动往 `~/usr/local/bin` 预装 GNU coreutils 9.10
  （本机实测新增 90 个文件、均为新增未覆盖既有文件），属框架既有行为。
- 上游测试与消费者测试数字在 本笔记 / `test_package/MANIFEST.yml` / PR 正文
  三处同源：上游 28、消费者 8。

### 对话 #1

2026-10-15：取源（R39 端点实测 + Debian pristine 交叉核对）→ preflight RC=0 →
recipe-search 无相似配方 → 精确核 `libblkid`/`xxd` 二进制已发布 → 框架裸构建
Step3/Step4 全绿 → 定位内核版本双层闸 → 逐项排掉 E011/E386/E468/组件子目录/
xxd/jobserver 七处 → 配方首稿 → `conan-verify` 三轮（ModuleNotFound → 下载
sidecar → `env cd`）后 G0–G4+L2/L4/L5 **全 PASS**，上游 23/23、消费者 8/8。
---

**编译结束**: 2026-10-15 03:12
**最终状态**: built
