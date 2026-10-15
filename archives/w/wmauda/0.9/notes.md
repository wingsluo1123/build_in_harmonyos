# wmauda 0.9 — 适配笔记

## 源码概述

wmauda 是 WindowMaker/Fluxbox dockapp，通过 D-Bus 控制 Audacious 媒体播放器。
单文件 C 项目（wmauda.c，873 行），Makefile 构建，无 configure 脚本。

## 上游信息

- 上游官网：https://www.netswarm.net/
- Debian 源码：http://ftp.debian.org/debian/pool/main/w/wmauda/wmauda_0.9.orig.tar.gz
- 作者：Christian Birchinger <joker@netswarm.net>, Michael Stewart
- 许可证：GPL-2.0-or-later
- 上游版本：0.9（2012 年发布，无后续更新）

## 依赖清单

| 依赖 | 版本 | 用途 |
|------|------|------|
| gtk2 | 2.24.33 | GTK+2 GUI widgets |
| dbus-glib | 0.114.1 | D-Bus GLib bindings |
| libaudclient | 3.5-rc2.1 | Audacious D-Bus client stub |
| dbus | 1.14.10 | D-Bus message bus |

全部依赖已在制品仓发布，无缺失。

**依赖版本选择说明**：libaudclient 在制品仓同时存在 `3.5-rc2` 与 `3.5-rc2.1`。
`3.5-rc2` 的配方硬依赖 `glib/2.88.0` + `dbus-glib/0.114`，与本图的 GTK+2 栈
（gtk2/2.24.33、pango、atk、gdk-pixbuf 均精确 pin `glib/2.84.0.1`）冲突：
override 传播到整图后，该版本的 package_id 在注册表中不存在，CI worker 只能
从源码重建，而其配方按“glib 为 static”假设只收集 `.a`，在 shared-only 的
`glib/2.84.0.1` 上链接期报一片 `-lglib-2.0/-lgio-2.0/-lgobject-2.0/-lgthread-2.0/-lgmodule-2.0`
找不到（PR #14869 / build #81368 的失败点）。`3.5-rc2.1` 的配方已 pin
`dbus-glib/0.114.1` + `glib/2.84.0.1`，其 package_id 与本图计算结果一致，
注册表中已有对应二进制（`0e0a65f8…`），因此本配方直接消费已发布二进制，
不再触发依赖的源码重建。

## 构建适配

1. **PKG_CONFIG_PATH 注入**：Makefile 使用 `pkg-config audacious/dbus-1/audclient/gtk+-2.0`
   获取 CFLAGS 和 LIBS。构建时设置 PKG_CONFIG_PATH 指向依赖包的 .pc 文件目录。

2. **CC/AR/RANLIB 传入**：遵循 R33 规则，从 Conan conf 获取编译器路径，
   不依赖 shell 环境变量 `${CC}`。

3. **PREFIX 设置**：Makefile 的 `install` 目标使用 `$(DESTDIR)$(PREFIX)` 安装，
   构建时传入 `PREFIX=${package_folder}`。

## 上游测试

wmauda 上游无自动化测试：
- Makefile 只声明 `all` / `clean` / `install` 三个目标，**没有 `check` 目标**
  （不是 automake 为无测试项目生成的空壳 check，而是该目标根本不存在）
- 无 tests/ 目录
- 无 configure/ac/meson 等测试框架

上游用例数 = 0（如实记录 0/0，不虚报），核验入口仅 `wmauda.c` + `Makefile`。

## test_package 消费者验证（test.sh，17 断言 + 1 鸿蒙用例）

测试逻辑落在 `test_package/test.sh`（CI L0c 要求 test_package/ 下必须有
`.c/.cpp/.cc/.cxx/.sh/.py` 测试源文件，`conanfile.py` 不计入），
`test_package/conanfile.py` 只做 bash 派发。

wmauda 的 `main()` 在 `getopt_long()` **之前**调用 `gtk_init()`
（`src/wmauda.c:833`），因此 `-v`/`-h` 同样需要 X display——无 DISPLAY 时
不存在可用的参数路径。故全部检查都落在「显示无关」路径上：

| # | 断言 | 说明 |
|---|------|------|
| 1-2 | 已安装二进制在 PATH 上且可执行 | VirtualRunEnv 暴露包 bin 目录 |
| 3-4 | OHOS ELF 形状 | ELF64 + AArch64 |
| 5 | 无 RPATH/RUNPATH | 包可重定位 |
| 6-7 | 运行时 pixmap 数据已安装 | `share/pixmaps/wmauda.xpm` + `dock-master.xpm`（非空） |
| 8 | man page 已安装 | `share/man/man1/wmauda.1`（非空） |
| 9-13 | 真实 DT_NEEDED 链 | libgtk-x11-2.0.so.0 / libgdk-x11-2.0.so.0 / libaudclient.so.2 / libglib-2.0.so.0 / libX11.so.6 |
| 14 | `audacious_remote_*` 未定义符号 | 证明 libaudclient 的 Audacious D-Bus 客户端 stub 真正被链接使用 |
| 15 | `dbus_g_*` 未定义符号 | 证明 dbus-glib 绑定真正被引用 |
| 16 | DT_NEEDED 闭包在 OHOS 可完整解析 | musl 运行时基线由加载器提供，另行断言 |
| 17 | 请求 `libc.so` | 符合 OHOS musl 目标预期 |

另有 **1 个鸿蒙特有已执行用例**（门控于宿主内核，门本身不是断言）：
无 X server 下端到端启动已安装二进制，预期干净拒绝
`cannot open display`（exit 1）——该行为恰恰证明 OHOS musl 加载器已解析
整条 DT_NEEDED 链（实测 63 项，含 `libaudclient.so.2`）且 GTK+2 初始化被真实
到达；若出现动态链接器中止（exit 127）或信号死亡（exit ≥ 128）则说明消费者
路径在鸿蒙上不可用。

## CI 失败修复记录（L0c no_test_sources + L0k commands_json_r38）

首轮 CI（PR #14869 / build #80201）在 `conan-build-test` 的 **L0 质量门禁**即
失败，包本体未编译（L1/L2/L4/L5 全部 skip）：

```
[fail] L0c: No test source files in test_package/
[fail] L0k: CLI tool detected but commands.json missing (R38)
```

**根因 1（L0c）**：PR 分支的 `test_package/` 只有 `conanfile.py` + `MANIFEST.yml`。
测试逻辑虽然真跑 `self.run`，但全部内联在 `conanfile.py` 里，而 L0c 的源文件
白名单是 `.c/.cpp/.cc/.cxx/.sh/.py` 且**显式排除 `conanfile.py`** → 判无测试源。
本地 W3 之所以「假绿」：conan 在 `test_package/` 就地生成的
`conanbuild.sh`/`conanrun.sh`/`deactivate_*.sh` 等恰好命中 `.sh` 白名单，
而 CI 是全新 checkout、不存在这些生成物。

**根因 2（L0k）**：`archives/w/wmauda/commands.json` 只存在于本地工作树而
从未 `git add`，CI 全新 checkout 看不到该文件。wmauda 的
`package_type = "application"` 且 `cpp_info.bindirs = ["bin"]` → 判定为 CLI 工具，
必须有软件级 commands.json。

**根因 3（L0k 之后的隐藏雷，同步修复）**：原 `build()` 用
`glob.glob("/data/storage/el2/base/cache/conan-home/p/glib*/p")` 这一**硬编码
沙箱缓存路径**来补 glib 的 include/lib 目录，而 CI worker 的 `CONAN_HOME` 是
`$HOME/.conan2`（`ci/conan/setup.sh:115`、`cleanup.sh:13` 均默认该值），该路径
在 worker 上不存在 → `glib_pkg` 为 `None` → 链接报一堆 `g_free`/`g_strdup`/
`g_object_unref`/`g_type_check_instance_cast` 等未定义符号。
**实测取证**（把该函数临时改为 `return None` 复现，`.ci_logs/expA-conan-create.log`）：
`-lgtk-x11-2.0 … -latk-1.0 … -laudclient -ldbus-glib-1 -lz -ldbus-1 -lexpat`
——glib 家族库名 **全部缺失**，而 `-L…/glib…/p/lib` 与 glib 的 `-I` 路径均在
（说明 glib 确实在 `self.dependencies` 图中，问题只在**库名**）。
根因是 **glib 把库声明在 `cpp_info` 组件（components）里**，顶层
`cpp_info.libs` 为空，只读顶层即静默丢库。

**修复**：
1. 新增 `test_package/test.sh` 承载真实消费者测试（17 断言 + 1 鸿蒙用例）；
   `conanfile.py` 改为 bash 派发（`CONFIG_SHELL` fallback，OHOS
   `/system/bin/sh` 不能可靠执行 ELF）。
2. 提交软件级 `archives/w/wmauda/commands.json`（name=wmauda / type=tool /
   versions.0.9.ref=wmauda/0.9 / binary=true）。
3. `build()` 删除硬编码缓存路径与 `_find_in_cache`，改为在依赖图遍历中通过
   `_dep_libs()` 一并收集 **CppInfo 组件库名**（`dep.cpp_info.components[*].libs`），
   配方行为与 `CONAN_HOME` 无关，在 CI worker 上同样成立。
4. 补 `manifest.yaml` 缺失的必填字段 `build_date` 与扁平
   `test_passed`/`test_failed`，并同步 `test_results` 明细与 `knowledge_gained`。

**复现/修复取证**：
- 修复前（禁用缓存路径）：链接失败，`ld.lld: error: undefined symbol: g_free`（等 7 个 glib 符号）
- 修复后：`-lglib-2.0 -lgobject-2.0 -lgmodule-2.0 -lgthread-2.0 -lgio-2.0` 齐备，`conan create` EXIT=0
- `test_package` 输出：`[consumer] RESULT: 18 passed, 0 failed`
  （DT_NEEDED 闭包 62/62 可解析 + 1 个鸿蒙消费者用例通过）

## OHOS 适配说明

wmauda 是 GUI 应用，运行时需要 X server + D-Bus session bus。
OHOS 无桌面会话环境，但编译产物可通过 conan 消费。
共享库 closure 加载验证确保 OHOS musl 兼容性。

## 对话记录

### 对话 #1 [2026-10-15]
- 问题: PR #14869 / CI build #81368 失败在依赖的源码重建上——图内 `libaudclient/3.5-rc2`
  的 package_id 因整图 glib override（2.84.0.1）在制品仓中不存在，CI 只能 `--build=missing`
  从源码重建；而该版本配方按「glib 为 static」假设只收集 `.a`，在 shared-only 的
  `glib/2.84.0.1` 上链接期报 `-lglib-2.0` / `-lgio-2.0` / `-lgobject-2.0` /
  `-lgthread-2.0` / `-lgmodule-2.0` / `-lintl` / `-lffi` 全部找不到。
- 操作: 依赖侧修复已作为 `libaudclient/3.5-rc2.1` 合并并发布（配方 pin
  `dbus-glib/0.114.1` + `glib/2.84.0.1`，其 package_id `0e0a65f8…` 与本图计算结果一致）。
  本配方把 requires 由 `libaudclient/3.5-rc2` 改为 `libaudclient/3.5-rc2.1`，
  并同步版本级 manifest、notes 与软件级 README/manifest。
- 结果: 清空本地 `libaudclient/*` 缓存后 `conan create` EXIT=0，图解析为
  `libaudclient/3.5-rc2.1#6b585c49…:0e0a65f8…#5ebe7822… - Download (ohpcd)`（不再源码重建）；
  同轮本地重跑的 `libxrender/0.9.12` 与 `pango/1.50.14.1.1` 源码重建也均 `Package created` 成功。
  W3 本地 CI：L0i 逐个依赖在制品仓命中（含 libaudclient/3.5-rc2.1），`Success 1/1 (100%)`，
  `test_package` 18 passed / 0 failed。

## 状态

- status: built
---

**编译结束**: 2026-10-15 13:36
**最终状态**: built
