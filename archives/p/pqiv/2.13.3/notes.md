# pqiv 2.13.3 适配笔记

## 编译环境
- 构建系统: 上游自带 `configure`（自写 bash 脚本，非 autotools）+ `GNUmakefile`
- 编译日期: 2026-10-15
- 平台: HarmonyOS PC / aarch64，**原生 build=host**（非交叉）
- 编译器: clang 15（从 profile `tools.build:compiler_executables` 获取，R33）
- 状态: built（本地 conan-verify + CI 同构门禁通过；未上传制品仓）

## 编译步骤（配方内实际执行）

```sh
# generate(): PkgConfigDeps 生成私有 .pc 集 + gdk-3.0 / gio-unix-2.0 shim
# build():
PKG_CONFIG_PATH=<generators> CC=/data/service/hnp/bin/clang \
  /data/service/hnp/bin/bash ./configure --prefix=/ --gtk-version=3 --backends=gdkpixbuf
PKG_CONFIG_PATH=<generators> CC=/data/service/hnp/bin/clang make -j8
PKG_CONFIG_PATH=<generators> ./pqiv --version        # 上游 CI 等效校验
# package():
PKG_CONFIG_PATH=<generators> CC=... make install DESTDIR=<package_folder>
```

最终产物 `bin/pqiv`（单文件 ELF，含 gdk-pixbuf 后端；`share/man/man1/pqiv.1`、
`share/applications/pqiv.desktop`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `PKG_CONFIG_PATH=... ./configure` 会被判 `Unknown option` 退出 1 | 上游自写 configure 只认自己 `case` 里的参数；`VAR=value` 形式落到 `*)` 分支被当成未知开关 | 不把 `PKG_CONFIG_PATH`/`CC` 作为 configure 参数；以**环境变量前缀**注入（`VAR=... sh ./configure`）。严禁 `--host/--build/--target`（铁律 #0） |
| 2 | configure 含 bash 专有语法（`${VAR//\{/(}`、`${CROSS: -1}`） | OHOS `/bin/sh` 是 mksh，不兼容 bash 参数展开 | 用 `CONFIG_SHELL`（`/data/service/hnp/bin/bash`）驱动；直接用 `bash ./configure` |
| 3 | `pkg-config --exists gdk-3.0` / `gio-unix-2.0` 失败 | PkgConfigDeps 只为 conan **组件**（`gtk+-3.0`、`gio-2.0`）生成 .pc；Makefile 还按模块名直接要求 gdk-3.0 与 gio-unix-2.0 | generate() 派生 shim：`gdk-3.0.pc`（改自 gtk+-3.0.pc，Libs 含 `-lgdk-3`）、`gio-unix-2.0.pc`（`Requires: gio-2.0`），写入 generators 私有前缀 |
| 4 | 可能误加 X11 依赖 | Makefile 依 `pkg-config --variable=targets gtk+-3.0` 含 `x11` 才追加 | 实测 ohpcd `gtk/3.24.43` 为 broadway 后端（`targets` 为空）→ 分支不触发；源码 X11 头由 `#ifdef GDK_WINDOWING_X11` 保护，不编译 |
| 5 | 可选后端自动探测可能引入未发布依赖 | 上游默认自动探测 poppler/spectre/wand/libav/libarchive/libwebp | 显式 `--backends=gdkpixbuf`，只保留内置后端，依赖面最小 |
| 6 | `make -j8` 打印 `jobserver mkfifo ... Operation not permitted` | TMPDIR 下无法建 jobserver fifo | 非致命：make 串行回退并完成构建（日志有全部 `CC`/`CCLD` 行） |

## 源码修改

无补丁（`patches: {}`）。依赖注入完全由 PkgConfigDeps + PKG_CONFIG_PATH + 两个 .pc shim 完成，未改上游源码。

## 依赖版本

- gtk/3.24.43（传递：glib/2.84.0.1、cairo/1.18.4、cairo-gobject/1.18.4.2、pango/1.50.14.1.1、
  gdk-pixbuf/2.44.6.1、atk/2.38.0.1.1、fribidi/1.0.16、libepoxy/1.5.10、harfbuzz/14.2.0.1.1.1 等）
- gdk-pixbuf/2.44.6.1（pqiv 直接使用 gdk-pixbuf-2.0）

## 验证结果

### 门禁逐项（真实命令与退出码）

| 门禁 | job id | 退出码 | 结果 | 日志 |
|------|--------|--------|------|------|
| conan-verify（G0/G1/G2/G3/G4 + 消费者测试） | `pqiv-verify-20261015-1` | 0 | PASS | `<runs>/pqiv-verify-20261015-1/output.log` |
| CI 同构 `ci/conan/build_and_test.sh` | `pqiv-ci-gate-20261015-2` | 0 | L0 pass / L1 pass / L2 skip / L4 pass / L5 pass | `<runs>/pqiv-ci-gate-20261015-2/output.log` |

- `L0`：L0i 依赖发布检查（gtk/3.24.43、gdk-pixbuf/2.44.6.1 均可 `conan download`）、L0j 首发布、
  L0k commands.json 有效、L0m 目录结构合规 —— 全通过。
- `L1`：L1a/L1b test_package 真实执行；**L1e 破坏性反向验证通过**（移走 `bin/` 后重跑 `conan test`
  必然失败 → 测试确实依赖本包产物）。
- `L2`：**skip（非阻断）**。CI 脚本在此直接执行 `bin/pqiv --version`（不经 conanrun），
  加载器找不到 gtk/glib 等 conan 依赖 .so 而失败。见「未验证项」。
- `L4`：无补丁，pass。`L5`：`bin/` 有内容，pass。

### 上游测试（R51 三步法）

- **清点**：上游 2.13.3 **无测试套件** —— 源码树无 `test/` 目录；`GNUmakefile` 无 `check` 目标
  （设备实测 `make -n check` → `No rule to make target 'check'`）；`.github/workflows/ci.yml`
  的 `check` 步骤仅为 `./configure && make && ./pqiv --version`。
- **执行**：`build()` 内复跑上游 CI 等效命令 `./pqiv --version`（失败即中止构建）。
- **计数**：上游注册测试程序 **TOTAL=0**；上游 CI 等效校验 1 项 → PASS=1 / FAIL=0 / SKIP=0 / NOT_RUN=0。

### 消费者测试 test_package（R34，实跑安装后的 bin/pqiv）

`test.sh` 在 conanrun 环境实际运行包内二进制，共 3 项断言：

- 断言 1：`pqiv --version` 输出精确匹配 `pqiv 2.13.3` —— PASS
- 断言 2：`pqiv --help` 含真实选项面（`Powerful quick image viewer` 与 `--version`）—— PASS
- 断言 3：非法选项使 pqiv 以非零码退出 —— PASS

TOTAL=3，PASS=3，FAIL=0，SKIP=0，NOT_RUN=0（证据：`reports/conan-create.log` 测试段落）。

### smoke 与鸿蒙特有测试

- smoke（CI L2）：尝试 `bin/pqiv --version`，因脱离 conanrun 环境无法解析动态依赖 → 未运行/跳过（非阻断）。
- 鸿蒙特有测试：无。

### 未验证项（如实声明）

1. **图形功能未在真机显示栈验证**：pqiv 的实际图像渲染需要一个显示后端；ohpcd `gtk/3.24.43`
   以 broadway 后端构建，本次仅在无显示环境验证了可执行性与 CLI 契约，未验证窗口/图像显示。
2. **L2 冒烟在 CI 的裸环境中为 skip**：需 conanrun（或等效 `LD_LIBRARY_PATH`）才能加载动态依赖。
   `test_package` 已在 conanrun 中实际执行同一二进制，作为等效功能证据。
3. 未做 W4 独立审查、未上传制品仓、未推送/建 PR（留给主会话）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pqiv | 主程序（GTK+3 / broadway 后端，gdk-pixbuf 后端；单文件 ELF） |
| share/man/man1/pqiv.1 | man page |
| share/applications/pqiv.desktop | 桌面条目 |

## 注意事项

- R33：编译器经 `self.conf.get("tools.build:compiler_executables")` 获取，不裸用 shell `$CC`。
- R38：应用型产物 → 已在软件级目录提供 `archives/p/pqiv/commands.json`。
- 铁律 #0：原生 build=host，未给 configure 传 `--host/--build/--target`。
- 本地 CI 门禁需带正确的 PR 文件清单：本 worktree 的 `origin` 指向陈旧离线包，`origin/main...HEAD`
  会退化为全仓扫描导致 JC 误报；以 `JUNK_PR_DIFF=<本次改动清单>` 复现平台 pr.diff 语义后 JC 通过
  （详见 `pqiv-ci-gate-20261015-1` 对比 `-2`）。
