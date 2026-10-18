# tofi 0.9.1 适配笔记

## 编译环境
- 构建系统: meson (C2x)，设备原生 build=host
- 编译日期: 2026-10-18
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，取自 profile 的
  `tools.build:compiler_executables`）
- Conan: 2.29.1；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / Release）
- 状态: built（本地 conan-verify G0–G3 + 消费者测试通过，尚未平台 upload）

## 上游信息
- 上游: https://github.com/philj56/tofi，tag `v0.9.1`
- tarball: `https://github.com/philj56/tofi/archive/refs/tags/v0.9.1.tar.gz`
- sha256: `dd55347b509af786f133def64f3a86f1db258b5e196de80e53d62827bdcc37bc`（430699 bytes，本机实测；
  与 `https://codeload.github.com/philj56/tofi/tar.gz/refs/tags/v0.9.1` 字节完全一致）
- 许可证: MIT；形态: wlroots 系 Wayland 启动器（C2x + meson），安装 `bin/tofi` 与
  `bin/tofi-run`/`bin/tofi-drun` 两个符号链接，内部工具 `tofi-compgen`（install: false）
- 包类型: `application`（桌面 CLI 工具）

## 编译步骤（已固化为 conanfile.py）

```bash
conan create archives/t/tofi/0.9.1 \
  -pr:h=<root>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<root>/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方内部顺序：
1. `source()`：下载 tofi v0.9.1 + wayland 1.24.0 源码（后者仅用于编译静态 scanner）。
2. `generate()`：`MesonToolchain` + 自写 `wayland-scanner.pc`/`wayland-protocols.pc`，
   复制改写全部依赖 `.pc`（prefix/libdir/includedir + 根相对 `-L//lib` 形态）并置顶
   `pkg_config_path`；注入 `llvm-ar`/`llvm-ranlib` 到 native file；用
   `extra_cflags`/`extra_ldflags` 提供各依赖的 include 根与 `musl-fts` 的 `-L`。
3. `build()`：先静态编译 `wayland-scanner`（**必须在 meson setup 之前**，因为
   `dependency('wayland-scanner', native: true)` 会检查其存在），再
   `apply_conandata_patches()` → `meson.configure()` → `meson.build()` → `meson.test()`。
4. `package()`：`meson.install()` 后用 `binary-sign-tool sign -selfSign 1` 重新签名
   `bin/tofi`（E077）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `get()` 报 `BadZipFile: File is not a zip file` | codeload URL 末段是无扩展名的版本号（`.../tar.gz/refs/tags/v0.9.1`），conan 的 `get()` 按扩展名判类型并回退到 zip | 换用等价的官方形态 `https://github.com/philj56/tofi/archive/refs/tags/v0.9.1.tar.gz`（实测同字节同 sha256） |
| 2 | `meson.build:136: ERROR: C shared or static library 'fts' not found` | musl（OHOS）既无 `fts.h` 也无 `fts_read()`，上游用 `cc.find_library('fts', required: not cc.has_function('fts_read'))` | `requires("musl-fts/1.2.7")`，并把它的 `-L` 注入 `extra_ldflags`（该依赖不走 pkg-config，MesonToolchain 不会转发） |
| 3 | `fatal error: 'cairo/cairo-ft.h' file not found` | cairo.pc/pangocairo.pc/harfbuzz.pc/freetype2.pc 只给 `-I${includedir}/<子目录>`，而上游按 `<cairo/cairo.h>` 形式包含；发行版上靠 `/usr/include` 隐式命中，Conan 前缀不在默认搜索路径 | `generate()` 把每个依赖的 `include` 根加入 `extra_cflags` |
| 4 | `error: conflicting types for 'basename'`（`src/config.c`、`src/history.c`） | OHOS sysroot 的 `<string.h>` 在 `_GNU_SOURCE` 下声明 K&R 的 `char *basename();`，`-std=c2x`（上游 default_options）下等价 `(void)`，与 `<libgen.h>` 的 `char *basename(char *)` 冲突；**两种 include 顺序都冲突** | 补丁 `0001`：`src/config.c` 只用 `dirname()`，改为直接声明 POSIX `char *dirname(char *);`；`src/history.c` 未使用任何 libgen 符号，移除该 include。上游调用点均未改动 |
| 5 | `ld.lld: error: unable to find library -lfreetype`（100 个目标全部编译通过，仅链接失败） | `freetype2.pc` 把 `libdir=//lib` 与 `Libs: -L//lib -lfreetype` 写死（打包 prefix 为 `/`），只改 `libdir=`/`includedir=` 变量够不到 `Libs:` 行里的字面路径 | `.pc` 改写增加根相对 `-L`/`-I` 重写（`-L//lib`、`-L/lib`、`-L/usr/lib`、`-I/usr/include` 等 → 实际包目录） |
| 6 | 安装后的 `bin/tofi` 在设备上不可执行（`Operation not permitted`） | meson 安装期就地改写 ELF（RUNPATH 的构建机绝对路径 → 占位符），使链接器写入的 `.codesign` 失效（E077） | `package()` 末尾先 `llvm-objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1`；日志实测 `add codesign section success` |
| 7 | 依赖图 `Version conflict: expat/2.8.2 vs 2.8.2.1` | wayland/1.24.0 要 expat/2.8.2（其 `.so` 无 SONAME），fontconfig/2.18.1.1 用干净重建的 2.8.2.1 | `self.requires("expat/2.8.2.1", override=True)`（libwayland-*.so 不链接 expat，仅 scanner 用） |

## 源码修改

- `patches/0001-ohos-config-libgen-basename-c2x-conflict.patch`（补丁 0001，portability）
  - `src/config.c`：`#include <libgen.h>` → 直接声明 `char *dirname(char *);`
    （该文件只用 `dirname()`；OHOS sysroot 下无法同时包含 `<string.h>` 与 `<libgen.h>`）
  - `src/history.c`：移除未使用的 `#include <libgen.h>`
  - 断言与行为不变：`config.c:312` 的 `dirname(tmp)` 调用点原样保留

## 依赖版本

`freetype/2.14.3` · `harfbuzz/14.4.0` · `cairo/1.18.4.2` · `pango/1.58.2` ·
`glib/2.84.0.1` · `wayland/1.24.0` · `wayland-protocols/1.48` ·
`libxkbcommon/1.13.1` · `musl-fts/1.2.7`；传递链（提升为直接 requires 以便
pkg-config 可见）：`expat/2.8.2.1` · `libffi/3.4.4` · `zlib/1.3.1.1` ·
`pcre2/10.45` · `pixman/0.46.4` · `libpng/1.6.58` · `fontconfig/2.18.1.1` ·
`fribidi/1.0.16` · `libthai/0.1.29` · `libdatrie/0.2.13`；构建工具 `meson/1.11.0`。

## 验证结果

上游测试（`meson.test()` 在 `build()` 内真实执行）：

```console
Ok:                2
Fail:              0
```

`meson-logs/testlog.txt` 的 TAP 实测：

| 目标 | TAP plan | ok | not ok | 说明 |
|------|----------|----|--------|------|
| `tofi:config` | `1..68` | 68 | 0 | `config_apply()` 取值校验 |
| `tofi:utf8` | `1..12` | 11 | 1 | 第 12 条为上游 `tap_todo("Needs composed character comparison")` 标注的**预期失败**，meson 不计入 Fail |
| 合计 | — | 79 | 1（TODO） | `N_executed = 80` |

⚠ 该套件是手写 TAP harness：`tap_not_ok()` 只打印 `not ok`，测试 `main()` 恒
`return EXIT_SUCCESS`（最小复现：断言失败而 `exit_code=0`）⇒ **退出码不能当判据**，
必须由 TAP 解析器（`protocol: 'tap'`）给出结论。详见新增知识草稿
`DRAFT-tofi-0.9.1-tap-exit-code-decoupled-suite`。

消费者测试（`test_package/src/test_tofi.sh`，对已安装产物执行）：

```
tofi consumer test: TOTAL=12 PASS=12 FAIL=0 SKIP=0
```

门禁：`conan-verify` **PASS**（G0/G1/G2/G3 全 PASS；G4 因工具取不到包 ID 未列，
L2/L4/L5 随之跳过，属工具侧限制，已在正文披露）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/tofi` | 见 `reports/conan-create.log` | 主程序（已重签名，含 `.codesign`） |
| `bin/tofi-run`、`bin/tofi-drun` | 符号链接 | 上游 `install_symlink` |
| `share/bash-completion/completions/tofi`（+ 两个符号链接） | — | bash 补全 |
| `etc/xdg/tofi/config` | — | 默认配置文件（`doc/config`） |
| `share/licenses/tofi/LICENSE` | — | MIT 许可证 |

## 注意事项

- 静态 scanner 依赖 SDK 自带 `libexpat.a`
  （`/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`）；按「SDK → 依赖包内」顺序查找，
  找不到显式抛 `ConanException`，不静默降级。
- 静态 scanner 的 wayland 版本必须与 `requires` 的 wayland 版本一致，配方内有显式校验。
- **`.codesign` 必须在所有 ELF 改动作业之后写入**：`package()` 先 `meson.install()`
  再签名，顺序不可颠倒（E077）。
- 运行期需要 `libfts.so.0`（musl-fts）；`package_info()` 已把它写进
  `runenv_info` 的 `LD_LIBRARY_PATH`，应用类包的传递共享依赖不会自动传播给消费者。
- 无图形环境时 `tofi` 仍能给出 `Couldn't connect to Wayland display.` 并退出 1；
  完整的合成器交互（wlr-layer-shell 渲染）在无 compositor 的 CI 中无法执行，
  消费者测试以「参数校验 + 无 display 路径」作为可执行最深行为，已如实披露。

## 证据路径（本机）

| 内容 | 路径 |
|------|------|
| conan-verify 输出 | `~/tmp/uc2/主理-7/tofi/verify-6.log` |
| conan create 原始日志 | `archives/t/tofi/0.9.1/reports/conan-create.log`（ignored，按需重生成） |
| conan-verify 报告 | `archives/t/tofi/0.9.1/reports/conan-verify-report.md` |
| 原始 TAP 日志 | `meson-logs/testlog.txt`（构建目录内，随 build 删除） |
| TAP 退出码最小复现 | `~/tmp/uc2/主理-7/tofi/taprepro/`（`repro.c` + 上游 `test/tap.c`） |
---

**编译结束**: 2026-10-18 04:48
**最终状态**: built
