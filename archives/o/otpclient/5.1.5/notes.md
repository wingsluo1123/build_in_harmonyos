# otpclient 5.1.5 适配笔记

## 编译环境

- 构建系统: cmake（上游 `CMakeLists.txt`，`cmake_minimum_required(VERSION 3.25)`）
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS aarch64，clang 15；profile `ci/conan/profiles/ohos-aarch64`，os=OHOS/6.0，armv8，libc++，Release）
- 语言: C（R47 语言预检实测：57 个 `.c` / 38 个 `.h`，零 C++ 文件，25,949 行；任务语言 cpp 与实测 C 属兼容族，不迁移）
- 状态: built

## 编译步骤

```bash
cd <repo>
conan create archives/o/otpclient/5.1.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

上游 CMake 目标：`OTPClient-cli`（CLI）、`OTPClient-search-provider`、
`OTPClient`（GTK4 GUI，受 `-DBUILD_GUI` 门控）、`tests/`（受 `BUILD_TESTING` 门控）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | `ConanException: Component 'glib::gobject' not found in 'glib' package requirement`（generate 阶段） | 上游依赖声明引用 glib **短组件名**（`glib::gobject`/`glib::glib`），而 OHOS `glib` 配方的组件名是 `glib-2.0`/`gobject-2.0`/`gio-2.0` 等长名；消费方 `PkgConfigDeps` 因此 abort | 复用仓库既有同构方案（参照 `libedataserverui4/3.60.2`）：`_normalize_glib_component_refs()` 在 `generate()` 中把依赖包 `cpp_info.requires` 的短名就地改写为长名 |
| 2 | `CMake Error at FindPkgConfig.cmake:639 … No package 'cotp' found`（configure 阶段） | 上游 `CMakeLists.txt:103` 用 `pkg_check_modules` 要 `cotp>=4.0.0` / `libqrencode`，而依赖包产出的 `.pc` 名是 `libcotp.pc` / `qrencode.pc`（其余 11 个模块名对齐） | `_align_pkg_config_names()`：对两个不匹配的依赖设置 `pkg_config_name` |
| 3 | `explicit_bzero` 隐式声明被 `-Werror=implicit-function-declaration` 拦死（`CMakeLists.txt:25` COMMON_C_OPTIONS） | `explicit_bzero` 是 glibc/BSD 扩展，OHOS/musl 未声明该 API；10 个源文件在调用（`src/common/{aegis,authpro,common,db-common,parse-uri,twofas}.c`、`src/gui/dialogs/*`、`src/gui/google-migration.c`、`src/gui/otpclient-application.c`、`src/search-provider/search-provider.c`） | **可移植口径**（非平台宏）：补丁 0001 在 `CMakeLists.txt` 增加**编译期能力探测**（`check_c_source_compiles` → `HAVE_EXPLICIT_BZERO`），探测失败时用 `add_compile_options(-include .../compat/explicit-bzero.h)` 强制包含兼容头；该头以配方 `exports_sources` 随包发布（**不是**补丁，见下节说明），以同名 `static inline` 实现（`memset` + `__asm__ __volatile__` 编译器屏障）兜底，不改上游行为 |
| 4 | `-std=c11` 下 musl 隐藏 POSIX 声明（`struct sigaction` 不完整类型 / `sigemptyset` 未声明） | 特性宏未开，strict c11 下 musl 不暴露 POSIX 扩展 | `generate()` 注入 `-D_GNU_SOURCE`（`extra_cflags` → `CMAKE_C_FLAGS`），对应知识库 E032 |
| 5 | 链接期 `undefined reference to 'g_libintl_gettext'` | `glib` 包自带 `libintl.h` 代理（`#define gettext g_libintl_gettext`），该符号只由 glib 包内 `lib/libintl.so` 导出；`libintl/0.26.1` 不含此 gnulib 改名符号 | 不能放全局链接标志：`CMAKE_EXE_LINKER_FLAGS` 会把 `-lintl` 落到 CMake 编译器自检链接行（此时无 `-L` 到 glib lib 目录）→ `unable to find library -lintl`。正解：`_append_intl_to_glib_pc()` 给上游实际使用的 `glib-2.0.pc`/`gio-2.0.pc` 的 `Libs:` 注入 `-lintl`（`-L` 由 glib 自身配置带入） |
| 6 | GUI 资源编译 `glib-compile-resources: exit 127`（`Error loading shared library libffi.so.8`） | 上游 `src/gui/CMakeLists.txt:5` **裸名**调用宿主工具 → 命中 PATH 上 HNP 系统版 `glib-compile-resources`（glib 2.38.2），其 RUNPATH 指向构建机路径（`/home/lycium++/...`），本环境无 `libffi.so.8` | 依赖包自带的同名工具在本机不可执行（见「注意事项」），且依赖链 8 个 libdir 里**没有** `libffi.so.8`，无法在不写死本地绝对路径的前提下补齐 → 本版本交付 CLI + search provider，`gui` 选项默认 `False`，保留 `-o gui=True` 开关 |
| 7 | 上游 CTest 全红（`0% tests passed, 13 failed out of 13`，0.26s 全挂，`Error relocating … g_strerror: symbol not found`） | 测试二进制**无 RUNPATH**，靠 `LD_LIBRARY_PATH` 解析；配方里 `self.run(env="conanbuild")` 用的是**构建**环境（只含 build-context 依赖），host 依赖的 libdir 不在其中 → 解析到系统 HNP 的 glib 2.38.2（不导出 `g_strerror`） | 测试改用 `env="conanrun"`（host 依赖 libdir 入 `LD_LIBRARY_PATH`） |

## 源码修改

补丁集（`patches/`，均在 `conandata.yml` 以 `patch_type: portability` 登记）：

| 补丁 | 内容 |
|------|------|
| `0001-CMakeLists.txt.patch` | 在 `include(CTest)` 之后插入 `explicit_bzero` 编译期能力探测（`check_c_source_compiles` → `HAVE_EXPLICIT_BZERO`）；探测失败时 `add_compile_options(-include ${CMAKE_CURRENT_SOURCE_DIR}/compat/explicit-bzero.h)` |

新增文件 `compat/explicit-bzero.h`（29 行）走**配方导出源**（`conanfile.py::export_sources` 的 `copy(self, "compat/*", ...)`）随包发布，**不做成「新建文件」型补丁**。原因（实测）：conan 2.x 用 `patch_ng` 应用补丁，创建型补丁（`--- a/新文件` + `@@ -0,0`）在目标父目录不存在时 `apply()` 返回 False → `ConanException: Failed to apply patch`；而「导出源」会被 conan 直接落到源码目录，`-include` 路径必然可解析。

补丁中**不含**平台宏（无 `__OHOS__`），走的是编译期能力探测，符合 R8 口径。

## 依赖版本

全部依赖均已发布到制品仓（W0/R36 实测 `conan download --only-recipe` 通过）：

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | 上游 GNOME 栈对齐版本；提供 gsettings/gio/libintl 代理 |
| gtk4 | 4.22.4 | GUI（本版本默认关闭，见问题 6） |
| libadwaita | 1.8.8 | GUI |
| gdk-pixbuf | 2.44.6 | GUI（上游要求 2.44.6.x） |
| libsecret | 0.21.7 | 密码存储后端 |
| libgcrypt | 1.11.0 | libsecret 依赖 |
| libcotp | 4.2.1 | 产出 `libcotp.pc`（上游要 `cotp`） |
| jansson | 2.15.1.1 | GUI/CLI 共用 JSON |
| protobuf-c | 1.5.1 | GUI |
| zbar | 0.23.93 | GUI 二维码 |
| libuuid | 2.42.2 | 提供 `uuid`（制品仓无独立 `libuuid` 包名之外的 `uuid`） |

## 验证结果

```bash
# 1) 全链路（第 12 轮，默认选项）
$ conan create archives/o/otpclient/5.1.5 -pr:h=…/ohos-aarch64 -pr:b=…/ohos-aarch64 --build=missing
CREATE_RC=0                     # 编译 + 测试 + 打包 + test_package 全通过

# 2) 上游测试（tests/CMakeLists.txt 注册 16 项：13 无条件 + 3 GUI 门控）
$ ctest --test-dir <build>/Release --output-on-failure --no-tests=error
100% tests passed, 0 tests failed out of 13

# 3) 消费者测试（test_package/test.sh，实际执行包内程序）
  otpclient-cli --version -> OTPClient version 5.1.5
otpclient consumer test passed

# 4) 数据编译产物（install 阶段宿主工具成品）
share/glib-2.0/schemas/gschemas.compiled   1660 B

# 5) 上游端到端冒烟 .ci/smoke-test.sh（26 条命令）
#    推进到 --import 步骤后停于平台权限模型，见下方「注意事项」
```

R51 上游测试申报表：上游有测试（`tests/` 目录 + 16 个 `add_test`）；实跑 **13/13 通过**；
未跑的 3 项（`otp_entry`/`google_migration`/`qrcode_parser`）**具体技术原因**：
三者都注册在 `tests/CMakeLists.txt:197 if(BUILD_GUI)` 内，GUI 关闭即不注册（GUI 关闭原因见问题 6）；
鸿蒙独有测试 = `test_package/test.sh` 3 项真实消费者断言（执行包内 `otpclient-cli` 校验版本输出、
`--help` 走通 GOption/glib 运行时链、schema 编译产物存在）。

## 交付物

本版本以 CLI + search provider 为交付面（GUI 见问题 6）：

| 产物 | 说明 |
|------|------|
| `bin/otpclient-cli` | OTP 管理 CLI（aarch64 ELF） |
| `bin/otpclient-search-provider` | KRunner 搜索提供者 |
| `share/glib-2.0/schemas/gschemas.compiled` | GSettings schema 编译产物 |
| `share/krunner/dbusplugins/*.desktop` | KRunner 桌面集成 |
| `share/bash-completion/completions/otpclient-cli` | CLI 补全 |

## 注意事项

1. **GUI 默认关闭的依据（可复现）**：上游 GUI 构建期必须执行宿主工具
   `glib-compile-resources`（`src/gui/CMakeLists.txt:5` 裸名调用）：
   - PATH 上解析到 HNP 系统版（glib 2.38.2）→ `exit 127`：`Error loading shared library
     libffi.so.8`（其 RUNPATH 指向构建机 `/home/lycium++/...`，本环境失效）；
     本机补上 `/data/service/hnp/libffi.org/libffi_3.4.4/lib` 到 `LD_LIBRARY_PATH` 后该工具
     实测可执行（`--version` 无 libffi 报错），但该路径是**本机绝对路径**，配方不得写死。
   - glib 依赖包自带同名工具，但本机执行报 `Operation not permitted`：conan 缓存中解出的
     二进制权限显示为 `-rwxrwx--- 20001006:file_manager`，本机 SELinux/HMDFS 标签规则下
     拷贝体与原件均不可执行（同机编译产物可正常执行，如 `otpclient-cli` 与测试二进制）。
   - 依赖链 8 个 libdir 实测均无 `libffi.so.8`，无法由依赖图提供。
   结论：GUI 需宿主工具可执行；`gui=True` 时 `src/gui/` 与 GUI 测试一并启用，宿主工具可用
   的环境下可直接 `-o gui=True` 验证。
2. **HMDFS 忽略 chmod（E046 族）**：上游 `.ci/smoke-test.sh` 走到 `--import` 时被 otpclient
   自身的安全守卫拒绝：
   `Refusing to open password file '…/dbpw': mode 0660 is readable or writable by group/other.`
   该守卫要求密码文件为 0600，而本平台下 `chmod 600` 不生效（文件权限恒 0660）→ 属**平台权限
   模型限制**，非包缺陷；同机 `ctest` 13/13 与消费者测试均通过。
3. **测试必须用 `conanrun` 环境**：本项目测试二进制不写 RUNPATH，`env="conanbuild"` 会解析到
   系统 glib 而缺符号（问题 7），改 `env="conanrun"` 后 13/13 通过。
4. **`.pc` 注入 `-lintl` 的位置**：不得放 `CMAKE_EXE_LINKER_FLAGS`（会落到编译器自检链接行），
   只能注入上游实际使用的 `glib-2.0.pc`/`gio-2.0.pc` 的 `Libs:`（问题 5）。
---

**编译结束**: 2026-10-16 09:51
**最终状态**: built
