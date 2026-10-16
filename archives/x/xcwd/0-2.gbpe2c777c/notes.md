# xcwd 0-2.gbpe2c777c 适配笔记

## 任务身份

| 项 | 值 |
|---|---|
| 工作区 | 本任务独立 git worktree（分支 `feat/xcwd-0-2.gbpe2c777c`） |
| 任务分支 | `feat/xcwd-0-2.gbpe2c777c` |
| 上游仓库 | https://github.com/schischi/xcwd |
| 上游版本锚点 | commit `e2c777cbf3a226522a4871f97916f0cb0bee3688`（2018-05-01） |
| 包版本 | `0-2.gbpe2c777c`（分支给定；`0-2.gbp<sha7>` 语义与 `archives/w/wyhash/0-2.gbp234f0c6` 同款） |
| 认领/绑定核查 | 本地分支已存在并与本任务包名/版本一致；**平台认领状态未核实**（本机无任务平台访问入口，见「注意事项」） |

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-10-15
- 设备: HarmonyOS PC，`uname -a` = `HarmonyOS localhost HongMeng Kernel 1.12.0 ... aarch64 Toybox`
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`，`/data/service/hnp/bin/clang`）
- Conan: 2.29.1，profile `ohos-aarch64`（`os=OHOS arch=armv8 compiler=clang 15`），原生构建（build = host = OHOS/aarch64）
- 状态: built

## 上游测试清点（R51 第 1 步）

上游**无测试套件**。清点证据（源码 = commit e2c777c 归档，解压根目录）：

| 检查 | 命令 | 结果 |
|---|---|---|
| 源码树文件清单 | `ls` | `.gitignore` / `LICENSE` / `Makefile` / `README.md` / `xcwd.c`（共 5 个文件，无 tests/、无 check/） |
| 测试目录 | `find . -type d -name "*test*" \| wc -l` | `0` |
| Makefile 测试目标 | `grep -inE "check\|test" Makefile` | 无匹配（Makefile:10 仅 `.PHONY: all clean distclean install`） |
| 其它测试框架 | 无 `ctest`/`pytest`/`meson` 注册 | 无 |

→ 属 TEST_QUALITY_SPEC「上游无测试」分支：适配后由 `test_package/` 提供覆盖，
已在 `test_package/MANIFEST.yml` 显式申报（`upstream_tests_exist: false` + 清点证据）。

## 编译步骤

探索阶段（模式 B）实际执行的命令与结果：

```bash
# 1. 精确源码归档（官方 GitHub archive 端点）
curl -sL -o xcwd-e2c777c.tar.gz \
  https://github.com/schischi/xcwd/archive/e2c777cbf3a226522a4871f97916f0cb0bee3688.tar.gz
sha256sum xcwd-e2c777c.tar.gz
# deb5ca6611abf3c8f435e42d9ac79b22ebbc82d5947a3fcf40ff7906d694e114

# 2. 依赖实测（W0：recipe + binary 双实证）
conan download "libx11/6.4.0" -r=ohpcd      # rc=0，含 binary（os=OHOS os.version=6.0）
conan download "xorgproto/2025.1" -r=ohpcd  # rc=0（header-only）
conan install --requires="libx11/6.4.0" -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=never
# Install finished successfully（libx11 + libxcb + libxau + libxdmcp + xtrans + xorgproto）

# 3. 上游 Makefile 原样执行（预期失败，作为平台闸证据）
make CC=clang
# Makefile:20: *** Operating System not supported..  Stop.

# 4. 实际可用构建（本轮探索）
make UNAME=Linux CC=clang \
  CFLAGS="-Wall -Wextra -std=gnu99 -O2 -DLINUX -I<libx11>/include -I<xorgproto>/include" \
  LDFLAGS="-L<libx11>/lib -lX11" -j1
# → xcwd（27008 字节，rc=0）
```

`conanfile.py` 已把第 4 步固化为配方（包含目录/库目录取自 Conan 依赖图，不写死路径）。

## 适配点

| # | 适配点 | 根因 | 解决方式 | 是否改源码 |
|---|--------|------|----------|-----------|
| 1 | 平台闸不认识 HarmonyOS | 上游 `Makefile:7` `UNAME:=$(shell uname)`，OHOS 的 `uname -s` 返回 `HarmonyOS`，既不等于 `Linux` 也不等于 `FreeBSD` → `Makefile:20 $(error Operating System not supported.)` | 命令行传上游自带的构建变量 `UNAME=Linux`，选中上游自身 Linux 分支（`/proc` + `glob`，OHOS bionic 下行为正确） | ❌ 否（`xcwd.c`、`Makefile` 与上游逐字节一致，`patches: {}`） |
| 2 | 命令行 CFLAGS 会静默丢弃 `-DLINUX` | GNU make 命令行变量优先级高于 makefile 内赋值，`ifeq` 分支里的 `CFLAGS += -DLINUX`（Makefile:14）被整体忽略；而 `LINUX`/`BSD` 两个 `#ifdef` 分支都定义了 `getProcesses()`/`readPath()`，丢宏不报错 → 静默编出功能缺失的二进制 | 在命令行 CFLAGS 中重述上游自带标志 `-Wall -Wextra -std=gnu99 -O2` **并**显式追加 `-DLINUX` | ❌ 否（配方侧完成） |
| 3 | 头/库路径来自依赖图 | `X11/Xlib.h`、`X11/Xfuncproto.h` 由 `libx11/6.4.0` + `xorgproto/2025.1` 提供，环境无系统 X11 | `build()` 从 `self.dependencies[...].cpp_info` 生成 `-I/-L`；编译器取自 `tools.build:compiler_executables`（R33/R49） | ❌ 否 |
| 4 | 不写 RUNPATH | OHOS 加载器拒绝指向 Conan 缓存目录的 `DT_RUNPATH`；本仓库 X11 包（如 `xsetroot`）惯例同样是纯 `DT_NEEDED` | 链接不加 `-Wl,-rpath`，运行期由 `conanrun` 提供搜索路径 | ❌ 否 |
| 5 | 不用上游 install 规则 | `Makefile` 的 `install:` 是 `install -m 0755 ${EXE} $(prefix)/bin`，无 `DESTDIR` 支持 | `package()` 直接把 `xcwd` copy 到 `package_folder/bin`（R20：DESTDIR staging 已废弃） | ❌ 否 |

## 源码修改

**无补丁。** `xcwd.c` 与 `Makefile` 与上游 commit `e2c777c` 逐字节一致；
系统级 `git status` / `refresh-patch --auto` 无需生成 `patches/`（`conandata.yml: patches: {}`）。

## 依赖版本

| 依赖 | 版本 | 用途 | 发布状态（实测） |
|---|---|---|---|
| libx11 | 6.4.0 | `X11/Xlib.h`、`-lX11`（`libX11.so.6`） | ✅ `conan download` rc=0（含 OHOS binary） |
| xorgproto | 2025.1 | `X11/Xfuncproto.h`（被 `Xlib.h` 引入） | ✅ `conan download` rc=0（header-only） |

传递依赖（由 libx11 配方引入，实测均已在制品仓）：`libxcb/1.16`、`libxau/1.0.11`、`libxdmcp/1.1.5`、`xtrans/1.6.0`。

## 验证结果

```text
# conan create（W3 / 干净复现，含 test_package）见 reports/ 与 .ci-result.json
# 探索阶段产物核对：
readelf -h   → ELF64 / AArch64 / DYN(PIE)
readelf -d   → NEEDED: libX11.so.6, libc.so；无 RPATH/RUNPATH
readelf -lW  → GNU_RELRO 存在、GNU_STACK 无 E（NX）
运行（无 DISPLAY，conanrun 环境）→ 退出码 1，stdout/stderr 均为空
运行（剥离 LD_LIBRARY_PATH）  → 加载器失败（无法定位 libX11.so.6），退出码非 0
```

消费者用例 **5 个 / 13 项检查全部通过**，逐项见 `test_package/MANIFEST.yml`。

### 未覆盖范围（如实声明）

OHOS PC **无 X 服务器**：设备上不存在 `Xorg`/`Xvfb`/`Xwayland` 可执行文件，
`/tmp/.X11-unix` 不存在，制品仓也无 `xorg-server`/`xvfb`/`xwayland`/`weston` 配方
（`conan list "xorg-server/*" -r=ohpcd` → 0 条）。因此以下依赖真实 X 会话的功能
**未在真机端到端验证**：

1. `focusedWindow()` 经 `XGetInputFocus`/`XQueryTree` 取焦点窗口句柄（xcwd.c:60-94）；
2. `windowPid()` 读取 `_NET_WM_PID`（xcwd.c:96-115）；
3. `WM_CLASS` 匹配回退路径（xcwd.c:117-145、319-327）；
4. `readPath()` 经 `/proc/<pid>/cwd` 解析最终工作目录并打印（xcwd.c:228-257）。

已用可验证的替代证据覆盖这些代码**是否真的被编入并被执行到入口**：HC-3 断言
仅存在于 `#ifdef LINUX` 分支的字面量（`/proc/%ld/cwd`、`/proc/[0-9]*`、`/stat`）
确在产物内；HC-2 真实执行程序并断言上游 xcwd.c:69-71 的无显示契约（退出码 1、
无输出），证明进程已加载并运行到 X 客户端初始化；HC-5 以负向验证证明运行期
确实加载 Conan 提供的 libX11。

## 注意事项

- **认领/绑定**：本机未提供任务平台入口（无平台 URL/凭据/任务 ID 环境变量），
  故「本人认领、任务活动、分支绑定」**尚未在平台侧核实**；本地分支名与包名/版本
  一致，归档目录为 `archives/x/xcwd/0-2.gbpe2c777c/`。
- 版本号含 `-`/`.`，Conan 引用写作 `xcwd/0-2.gbpe2c777c`；R37 的适配修复后缀
  尚未使用（首次适配）。
- `commands.json` 位于软件级 `archives/x/xcwd/`，`binary: false`（尚未经 release
  流水线发布）。
- 未发布前不要改 `manifest.yaml` 的 `status` 为 published。
---

**编译结束**: 2026-10-15 02:05
**最终状态**: built
