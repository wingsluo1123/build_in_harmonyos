# swupdate 2026.05.1 适配笔记（OpenHarmony / HarmonyOS PC aarch64）

## 选型与目标

- 上游：`https://github.com/sbabic/swupdate.git` tag `2026.05.1`
  （annotated tag 对象 `9ca7bc40ea33d76ea2f2d65d2bc142891a82892e`，
  解引用后的提交 `9000ecb52677da7d9676a61b729bab57dba99674` "Prepare 2026.05.1"；
  发行归档 `https://github.com/sbabic/swupdate/archive/refs/tags/2026.05.1.tar.gz`
  sha256 `26236a354e8cf21806d20a76728b3805ae49c23cfb2eb794fe91d1f0b280298e`）。
- 产物：`bin/swupdate`（更新代理本体）+ `bin/swupdate-client`、
  `bin/swupdate-progress`、`bin/swupdate-ipc`（IPC 工具）+ `lib/libswupdate.so.0.1`
  + `lib/lua_swupdate.so.0.1`（Lua 绑定）+ 3 个 IPC 头文件。
- 构建系统：Kbuild（kernel 风格 `make` + Kconfig + `scripts/Kconfiglib`），
  没有 configure/cmake，配方直接驱动上游 Makefile。

## 功能面（configs/ohos_defconfig，补丁 0004）

| 面 | 配置 | 依赖 |
|---|---|---|
| 镜像校验 | `CONFIG_HASH_VERIFY`、`CONFIG_SIGNED_IMAGES`、`CONFIG_SIGALG_RAWRSA` | openssl |
| 镜像加密 | `CONFIG_ENCRYPTED_IMAGES` | openssl |
| 下载 | `CONFIG_DOWNLOAD` | libcurl |
| 内置 web 服务器 | `CONFIG_WEBSERVER`、`CONFIG_MONGOOSESSL` | mongoose（包内） + openssl |
| hawkBit 客户端 | `CONFIG_SURICATTA`（含 `SURICATTA_HAWKBIT`） | json-c + libcurl |
| Lua 扩展 | `CONFIG_LUAEXTERNAL`、`CONFIG_LUASCRIPTHANDLER` | lua 5.4 |
| 归档处理器 | `CONFIG_ARCHIVE` | libarchive |
| 脚本/裸设备 | `CONFIG_RAW`、`CONFIG_SHELLSCRIPTHANDLER` | libconfig（恒链接） |
| 硬件兼容性 | `CONFIG_HW_COMPATIBILITY` | — |

**已启用的制品仓依赖**：libmtd/2.3.1-3 + libubi/2.3.1-3 提供 MTD/UBI
头与静态库，故 `CONFIG_MTD`/`CONFIG_CFI`/`CONFIG_UBIVOL` 打开（工具链侧的
`HAVE_LINUX` 由补丁 0005 打开），`test_flash_handler`（39 例）因此在位。

**被禁用的可选面**（OHOS 制品仓无对应包，配方显式 `HAVE_*=n`）：
libubootenv（U-Boot env / swupdate vars）、libubootebg / tegra-boot-tools
（EBG/CBOOT 引导）、zeromq（remote handler）、
librsync + zck（delta）、libwebsockets + uriparser（swuforwarder）、
zstd/xz/lz4（压缩面）、wolfssl/mbedtls（替代 TLS 实现）、gpgme（GPG 校验）、
libbtrfsutil（btrfs）。`uname -s` = `HarmonyOS` 另使 Kconfig 的
`HAVE_LINUX=n`，systemd/MTD 面自动收敛。

## 依赖接线（Kbuild 与 conan 的接法）

Kbuild **不做依赖自动探测**：`Makefile.deps` 只给默认 `export HAVE_XXX = y`，
真正读它的是 Kconfig 的 `option env=`；`pkg-config` 只用于 lua 与 p11-kit。
因此配方必须：

1. 环境里显式声明每个 `HAVE_*`（缺库给 `n`）——否则 Kconfig 会把对应代码面打开
   并在编译/链接期炸；
2. 头文件路径经 `CONFIG_EXTRA_CFLAGS` 注入（`Makefile.flags` 会把它并进
   `KBUILD_CFLAGS`，并被 `export` 到子 make）；
3. 库搜索路径经**环境变量 `LDFLAGS`** 注入——`EXTRA_LDFLAGS` 不会被导出到
   `test/` 的子 make，而 `LDFLAGS` 在上游 `Makefile:237` 被显式 `export`，
   主链接与测试链接都读它（这是单元测试二进制能链上的关键）；
4. 库名经 `CONFIG_EXTRA_LDLIBS` 注入（上游把它并进 `LDLIBS`，测试链接也复用
   同一份 `LDLIBS`）；
5. `PKG_CONFIG_PATH` 指向 `PkgConfigDeps` 生成目录 + `CONFIG_LUAPKG="lua-5.4"`
   让上游自己的 lua 探测命中（`-Wl,-E` 由该分支给出）。

## OHOS 适配点（补丁 0001–0006）

1. **`libubootenv` 是硬依赖，不是可选面**（补丁 0001）。上游
   `core/Makefile` 的 `obj-y` 恒含 `swupdate_vars.o`、
   `include/swupdate_vars.h` 顶层 `#include <libuboot.h>`、
   `Makefile.flags:112` 恒 `LDLIBS += pthread ubootenv json-c`，且
   `core/swupdate_vars.c` 直接调 `libuboot_*`。OHOS 侧：`conan list -r=ohpcd
   '*uboot*'` 0 命中（`u-boot-tools/2026.07` 只安装 bin 工具、不导出库与头），
   sysroot 无 `libuboot.h`。补丁把它收敛成显式可关闭面：新增 Kconfig
   `UBOOTENV`（`depends on HAVE_LIBUBOOTENV`，`default y`），`UBOOTENV=n` 时
   `pthread` 之外的 `-lubootenv` 不再出现、`swupdate_vars_*` 走 `#else` 分支返回
   `-ENOTSUP` / `NULL` / `false`（**不静默吞写操作**，调用方上游已有
   WARN/NACK 路径）。
2. **OHOS 无 POSIX 线程取消**（补丁 0002）。`readelf --dyn-syms libc.so`
   实测 `pthread_cancel` / `pthread_testcancel` / `pthread_setcanceltype`
   计数全 0（`pthread_create` / `pthread_kill` 为 1；`libpthread.a` 是 8 字节
   占位）。上游 `sigterm_handler()` 里 `pthread_cancel(network_daemon)` 直接
   链接失败（`ld.lld: error: undefined symbol: pthread_cancel`）。补丁按
   `__OHOS__` 分支改 `exit(exit_code)`：仍会跑到上游注释所述的 atexit() 收尾，
   且守护主循环不会永久卡在 `pthread_join()`；其他平台保持原样。
3. **测试二进制的 `LD_LIBRARY_PATH`**（补丁 0003）。`test/Makefile` 的
   `EXECUTE_TEST` 用 `LD_LIBRARY_PATH=$(objtree)` 整体覆盖继承值，设备上被覆盖
   掉的正是 conan 依赖（libssl/libcurl/libconfig/libjson-c…）目录。改为追加。
4. **`configs/ohos_defconfig`**（补丁 0004）。按 OHOS 制品仓实有依赖选定功能面
   （签名校验/加密、下载与 hawkBit、mongoose web 服务器、Lua、libarchive 归档、
   MTD/CFI/UBIVOL），不引用缺失项。
5. **`uname` 判据补 HarmonyOS**（补丁 0005）。`HAVE_LINUX` 是 MTD/UBIVOL 面
   （以及 `test_flash_handler` 单测二进制）的唯一总闸；上游只认
   `uname -s == Linux`，设备返回 `HarmonyOS` ⇒ `HAVE_LINUX=n` 会把
   `CONFIG_MTD/CFI/UBIVOL` 整体静默收敛（连带丢掉 39 例 `test_flash_handler`）。
   OHOS 是 Linux 内核 ABI 上的 ELF 用户态、MTD/UBI ioctl 同源，故把
   `HarmonyOS` 并入 Linux 分支；`HAVE_LINUX` 在 C 代码中零引用，其余平台行为不变。
6. **回移上游测试修复**（补丁 0006）。本 tag 的 `test/test_hash.c` 断言
   `swupdate_HASH_final()` 返回 1，而全部 provider 与全部调用方的约定是成功返回
   0（`core/cpio_utils.c:573`、`corelib/channel_curl.c:1510` 均以 `< 0` 判错），
   该用例在本机与上游 CI 均必失败。逐字回移上游提交
   `648eff6da1f0`（2026-07-29，晚于本 tag）：`assert_int_equal(error, 1)` →
   `assert_int_equal(error, 0)`，测试强度不变（仍校验 sha1/sha256 四组向量）。

## 设备侧另两处必需动作（配方层，非源码补丁）

- **`LD` / `HOSTCC` 必须显式给**：上游 `Makefile:190-191` 用
  `set_if_default_or_unset(LD,$(CROSS_COMPILE)cc)` 把 `LD` 默认成 **`cc`**
  （不是 `ld`），OHOS 无 `cc` 别名 ⇒ 链接期 `/bin/sh: cc: inaccessible or not
  found`；`HOSTCC` 默认也是 `cc`（`fixdep` 构建即失败）。配方把
  `CC`/`LD`/`HOSTCC` 一并钉到 profile 的 `tools.build:compiler_executables:c`。
- **`SKIP_STRIP=y`**：strip 会改写链接期自签的 ELF（见下条）。产物按 unstripped
  打包（体积换可用性，上游 `Makefile:457-459` 的官方开关）。
- **重签 OHOS ELF**：本项目链接出的 ELF，lld 自签段里的"文件长度"字段恒为
  `0x53740`（≠ 实际长度，实测 5.5–6.2 MB 四种产物同一常量）⇒
  `execve` 报 `Operation not permitted`（EXIT=126），即"fs 权限正常但就是起不来"。
  配方对 `bin/*` 与 `lib/*.so*` 统一 `llvm-objcopy --remove-section .codesign`
  + `binary-sign-tool sign -selfSign 1`（重签后 `--version` 正常）。
  单元测试二进制同样命中，且 `test/Makefile` 的 `%.lnk` 戳记从不创建 ⇒
  **每次 `make test` 都会重新链接**，所以重签挂在 `EXECUTE_TEST` 里、紧挨执行前
  （不改上游 runner 语义，只在每条用例前插一步签名）。

## 上游测试

- **单元测试**：`test/` 下 cmocka 用例，由 `make test` 构建并执行（TAP 输出）。
  本配置构建 9 个二进制共 **60** 例，全部通过；未构建 1 例
  （`test_crypt_pkcs11`，其夹具必须由 `softhsm2-util` 生成，设备与 worker 均无）。
- **验收测试**：`make acceptance-tests`（`scripts/acceptance-tests/CheckImage.mk`）。
  本配置启用 **6** 个目标，全部通过。两处设备适配：
  ① `SWU_CLEAN = rm -f /tmp/sw-description` 在只读 `/tmp` 上必失败，而
  check-only 流程从不创建该文件 ⇒ 以 `SWU_CLEAN=true` 消除清理步（语义等价）；
  ② `acceptance-tests` 以 `swupdate` 为前置目标，make 可能重新链接它从而作废
  `.codesign` ⇒ 配方先跑一次（允许重链）→ **重签** → `./swupdate --version`
  前置守卫 → 再跑一次做真实断言。守卫是必要的：6 个目标里 5 个是"必须失败"，
  二进制不可运行（rc=126/127）会让它们**假通过**。

## conan 静态包混装 .so 的处理（影子目录）

`libarchive/3.8.7` 在制品仓声明 `shared=False`，但 `lib/` 下 `.a` 与 `.so.13`
并存；链接器按同目录优先 `.so` 取动态库，产物带上 `DT_NEEDED
libarchive.so.13`，而 Conan 的 `VirtualRunEnv` 只导出 `require.run=True`（即
shared）依赖的目录 ⇒ 运行期 `Error loading shared library libarchive.so.13`
（且 `test_package` 的"必须失败"断言会假通过）。配方在 `generate()` 里为所有
`shared=False` 的依赖建一个只放 `lib*.a` 的影子目录并置于 `-L` 最前，使链接
回到该包声明的静态语义：修后 `readelf -d bin/swupdate` 的 libarchive 计数
1 → 0，运行期只剩 `libjson-c.so.5`/`libcurl.so`/`libconfig++.so`。同类坑记入
知识草稿 `E760`。

## 复现命令（设备）

```sh
. "$HOME/tmp/swupdate-2026.05.1/env.sh"
cd "$PACKAGE_DIR"
conan create . -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" -c tools.build:jobs=2
```
