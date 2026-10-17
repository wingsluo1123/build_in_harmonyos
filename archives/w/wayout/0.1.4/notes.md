# wayout 0.1.4 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build + protocol/meson.build）
- 编译日期: 2026-10-17
- 编译器: HarmonyOS 6.0 PC 环境 clang 15.0.4（aarch64-linux-ohos，musl）
- 状态: built

## 概述

wayout 把标准输入（feed）渲染成 Wayland 桌面上的 layer-shell 小部件：按行/空行/
自定义正则分隔刷新，支持 pango markup、颜色、边框、字号、位置。上游源自 wlclock。

源码 27 个文件（7 个 .c + 头文件 + 3 个协议 XML），协议绑定由 wayland-scanner 在
构建期生成（xdg-shell / xdg-output-unstable-v1 / wlr-layer-shell-unstable-v1）。

## 依赖核验（W0，`conan install --build=never` 实测）

| 依赖 | 上游要求 | 采用版本 | 结论 |
|---|---|---|---|
| wayland-client / wayland-cursor | 无版本下限 | wayland/1.24.0 | ✅ 二进制可用 |
| wayland-protocols | 无版本下限 | wayland-protocols/1.48 | ✅ |
| cairo | `dependency('cairo')` | cairo/1.18.4.2 | ✅ |
| pangocairo | `dependency('pangocairo')` | pango/1.58.2（提供 libpangocairo-1.0） | ✅ |
| wayland-scanner（native） | `native: true` | wayland/1.24.0 的 bin + staging | ✅ |
| scdoc（native，可选） | `man-pages` 特性 | **关闭**（`-Dman-pages=disabled`） | 不需要 |

> 版本冲突：`wayland/1.24.0` 要求 `expat/2.8.2`，而 `pango → fontconfig/2.18.1.1`
> 要求 `expat/2.8.2.1`。配方用 `self.requires("expat/2.8.2.1", override=True)` 统一；
> 实测 override 不改变 wayland 的 package_id（`conan install --build=never` 直接命中
> 已发布二进制，未触发任何重建）。

## 编译步骤

```bash
# 与实际 W3/CI 同源
conan create archives/w/wayout/0.1.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部：

1. `source()`：官方 SourceHut release tarball（sha256 校验）。
2. `build()`：先 `apply_conandata_patches`，再用 `meson configure/build`。
3. `generate()`：
   - `PkgConfigDeps` 生成标准 `.pc`；
   - **桥接 `.pc`**（`wayout_pkgconfig/`）：`wayland-cursor.pc`、`pangocairo.pc`、
     `wayland-scanner.pc`、`wayland-protocols.pc`（带 `pkgdatadir`），prefix 指向真实
     包目录（包内自带 `.pc` 以 `prefix=/` 安装，不可用）；
   - **staging wayland-scanner**：拷贝 → `patchelf --replace-needed` 把构建机绝对
     `DT_NEEDED` 改写为 `libexpat.so` → `llvm-objcopy --remove-section .codesign` →
     `binary-sign-tool` 重签名 → wrapper 注入 `LD_LIBRARY_PATH`；
   - `MesonToolchain.pkg_config_path` 前置桥接目录，关闭 `man-pages`；
   - meson 机器文件注入 `pkg-config`/`ninja`/`ar`/`ranlib` 绝对路径。
4. `package()`：`meson install` + LICENSE 入 `licenses/` + `bin/wayout` 自签名。

## 上游测试入口核验（R51）

上游**没有自动化测试套件**：

- sdist 27 个文件中不存在 `tests/`、`test/` 目录；
- `meson.build` / `protocol/meson.build` 中没有任何 `test()` 注册（`meson test`
  会报 "no tests defined"）；
- 仓库无 CI 测试配置；README 只给出手工运行示例（`cal | wayout`）。

可执行的真实验证入口（均已实跑）：

| 入口 | 命令 | 结果 |
|------|------|------|
| 构建 | `meson setup build && ninja -C build` | 通过（0 warning / 0 error） |
| CLI 契约 | `wayout --version` / `--help` | rc=0，输出版本/用法 |
| 真实协议连接 | `wayout --feed-line`（无合成器） | rc=1，`ERROR: Can not connect to a Wayland server.` |
| 正则错误路径 | `wayout -d '['` | rc=1，`invalid regex`（regcomp/regerror 实跑） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build` configure 报 `get_pkgconfig_variable` 不存在 | 该 API 在 Meson 1.6 已移除（本环境 meson 1.12 / 配方 meson 1.11） | 补丁 0001/0002 改为 `get_variable(pkgconfig: ...)` |
| 2 | `dependency('pangocairo')` 找不到 | Conan PkgConfigDeps 只按 `pkg_config_name` 生成 `.pc`（pango 包只声明 `pango`） | 桥接 `pangocairo.pc`（Requires: pango, cairo；Libs: -lpangocairo-1.0） |
| 3 | `dependency('wayland-cursor')` 找不到 | 同上（wayland 包只声明 `wayland-client`） | 桥接 `wayland-cursor.pc` |
| 4 | `dependency('wayland-scanner', native: true)` 找不到 | 同上；且 wayland 包的 `bin/wayland-scanner` 在 HMFS 上执行 EPERM（未签名 + 绝对 `DT_NEEDED`） | 桥接 `wayland-scanner.pc` 指向 staging 后的 wrapper；staging = patchelf + 去 `.codesign` + 重签 + LD_LIBRARY_PATH |
| 5 | `wp_dir = ... pkgdatadir` 为空 | PkgConfigDeps 生成的 wayland-protocols.pc 无 `pkgdatadir` | 桥接 `wayland-protocols.pc`（`pkgdatadir=${prefix}/share/wayland-protocols`） |
| 6 | meson 报 `pkg-config/ninja/ar` ENOENT | OHOS 上 Python subprocess 不能以裸名 spawn | 机器文件 `[binaries]` 注入绝对路径 |
| 7 | `src/output.c:22 -Werror,-Wstrict-prototypes` | `static void noop () {}` 是无原型声明，但被赋给多种 listener 函数指针槽位（改 `(void)` 会引发 6 处函数指针不兼容） | 补丁 0001 在 `add_project_arguments` 追加 `-Wno-strict-prototypes`，保留上游的"万能 no-op"意图 |
| 8 | 产物在设备上 `Error loading shared library ...` | 二进制无 RPATH，依赖库在 Conan 缓存 | 运行时用 `VirtualRunEnv`/`conanrun` 提供 `LD_LIBRARY_PATH`（Conan 应用包惯例）；CI L2 冒烟探测为非阻塞告警 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `patches/0001-meson.build.patch` | `meson.build` | `scdoc.get_pkgconfig_variable()` → `scdoc.get_variable(pkgconfig:)`；`add_project_arguments` 增加 `-Wno-strict-prototypes` |
| `patches/0002-protocol-meson.build.patch` | `protocol/meson.build` | `wayland_protocols.get_pkgconfig_variable('pkgdatadir')` 与 `wayland_scanner_dep.get_pkgconfig_variable('wayland_scanner')` → `get_variable(pkgconfig:)` |

补丁均为 Meson 新版本兼容性修复，无平台宏（`__OHOS__` 等），可无条件应用。

## 依赖版本

- wayland/1.24.0、wayland-protocols/1.48、cairo/1.18.4.2、pango/1.58.2
- 传递：glib/2.84.0.1、harfbuzz/14.4.0、fribidi/1.0.16、fontconfig/2.18.1.1、
  freetype/2.14.3、libpng/1.6.58、pixman/0.46.4、libffi/3.4.4、expat/2.8.2.1、
  libxml2/2.15.3、libthai/0.1.29、libdatrie/0.2.13、pcre2/10.45、zlib/1.3.1.1
- 工具：meson/1.11.0（tool_requires）、clang 15.0.4、ninja

## 验证结果

```bash
$ conan create archives/w/wayout/0.1.4 -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64
# exit code 0；0 warning / 0 error；28/28 消费者测试通过
```

- test_package 通用检查：**14 passed, 0 failed**（`reports/conan-create.log`）
- test_package 鸿蒙特有检查：**14 passed, 0 failed**
- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 **全部 PASS**
- 产物校验：ELF64 / AArch64 / `ld-musl-aarch64.so.1`；`DT_NEEDED` 含
  `libpangocairo-1.0.so.0`、`libpango-1.0.so.0`、`libcairo.so.2`、
  `libwayland-client.so.0`；设备上 `wayout --version` 可执行（说明全部依赖解析成功）。

## W3 本地 CI 模拟（通过）

```bash
$ python3 scripts/ohc-run.py finish wayout 0.1.4 built
  ℹ️ Step 5/10: 本地 CI 模拟 (W3) [阻塞门禁]...
  ✅   ✅ W3 本地 CI 模拟通过
```

`.ci-result.json`：`exit_code=0`、`integrity_hash=29bab68fb7dcb363`、
`log_sha256=4de3e559200be73ade27c1cf72b6b8ccb95d1c4c97e41d588d4c5d046275435c`。

门禁明细（`reports/w3-local-ci.log`）：

| 门禁 | 结果 |
|------|------|
| G0（知识图谱完整性） | pass（2140 entries） |
| KC（知识库质量） | pass |
| JC（杂项文件） | pass |
| L0（依赖/版本/commands.json/目录结构） | pass |
| L1 / L1e（test_package 实跑 + 破坏性反向验证） | pass |
| L2（`wayout --version` 冒烟） | skip：非阻塞告警（二进制无 RPATH，CI 未注入 Conan 运行时 `LD_LIBRARY_PATH`） |
| L4（补丁静态扫描） | pass |
| L5（产物基线） | pass |

### 过程中的一次阻塞（已在 main 侧修复）

首次 `finish` 的 W3 在**构建之前**就被 main 上既有知识库缺陷拦住（与 wayout 无关）：

- `G0b/G0d`（`ci/conan/build_and_test.sh`）与 `KC5`（`ci/scripts/knowledge_check.sh`）的正则
  仍按 3 位数 `E[0-9][0-9][0-9]`，而 main 已收录 `E1000`–`E1999`；
- `KC2` 把 `E1115/E1123/E1126` 的 `forbid_N_pattern` 误判为 `todo_in_content` 占位。

复现证据：`index.tsv 行数(1999) vs .kv(999) 不匹配` / `1000 个非标准命名的 .kv 文件`。
该缺陷随后由上游 `!16468 merge editor/ci-4digit-id-hotfix into main`（`d1a25afe76`）修复
（正则改为 `E[0-9]{3,}`，并给 `forbid_N_pattern` 及其续行加豁免）。本分支 rebase 到
该修复后的 main（`a9a60dda65`）后重跑，W3 通过。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/wayout` | 63936 | 可执行文件（aarch64 + musl，已自签名） |
| `licenses/LICENSE` | 35149 | GPL-3.0 |

`bin/wayout` sha256 = `bfce567f166887b0afcc80291ef5b61515a47f4cdd76f8d6eb805fd68ed233d5`

## 注意事项

- 运行需要实现了 `wlr-layer-shell` 与 `xdg-output` 的 Wayland compositor；
  HarmonyOS PC 默认没有，因此设备侧验证覆盖「加载/CLI 契约/真实 wl_display_connect
  失败路径」，未做真实渲染。
- 二进制无 RPATH，运行时必须由 Conan 运行时环境提供依赖库路径。
- 上游 README 的时钟示例写作 `while; do ...` 有笔误（缺条件），实际应写
  `while true; do ...`；属上游文档问题，未修改。
- 上游无自动化测试，test_package 是唯一的自动化验证层。
---

**编译结束**: 2026-10-17 14:00
**最终状态**: built
