# patman 1.2.2 适配笔记

## 编译环境
- 构建系统: makefile（无 configure）
- 编译日期: 2026-10-08
- 编译器: OHOS NDK clang++（`/data/service/hnp/bin/clang++`，profile `ohos-aarch64`）
- 状态: built

## 语言预检
- 只读判定：C++ 项目（3 个 .cpp + 3 个 .h，顶层 Makefile），默认口径 `lang-preflight` 通过（milestone=lang_checked）。

## 上游测试清点（R51）
- 上游源码包 12 个文件，无 `tests/` 目录，Makefile 无 `check`/`test` 目标，无 ctest/pytest 注册：上游测试 N=0。
- 由 `test_package` 补真实功能测试（见下）。

## 源码来源（PF7 / R39 登记例外）
- 使用 Debian 官方归档的 `patman_1.2.2+dfsg.orig.tar.xz`（任务指定）。
- 与上游官方 `https://bioinf.eva.mpg.de/patman/patman-1.2.2.tar.gz`（sha256 `0905ae2c…847dc`）逐文件比对：全部源文件相同，官方包仅多了预编译的 x86 二进制 `patman` 与 `.svn/` 目录（+dfsg 即移除它们）。
- 不直接用官方 URL 的原因：官方站点证书链不完整，Python/Conan 下载报 `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`（本机 W3 无法 `conan create`）；且官方包带有预编译二进制。

## 编译步骤
1. 依赖 `popt/1.16` 已在制品仓发布（`conan download popt/1.16 -r=ohpcd --only-recipe`）。
2. `conan create` 配方：`AutotoolsToolchain` + `AutotoolsDeps` 生成环境（CXX、CPPFLAGS=-I popt、LDFLAGS=-L popt），
   在源码目录执行 `make patman`；`package()` 直接复制 `patman`、`patman.1`、`LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 规则里写死 `g++` | Makefile 链接/编译规则硬编码主机编译器，环境变量 CXX 不起作用 | 补丁改为 `$(CXX)` |
| 2 | `-march=k8` | x86 专有架构参数，aarch64 clang 不认 | 补丁删除 |
| 3 | `-V` 输出 `revision 1.2` | Makefile `version := 1.2` | 补丁改为 `1.2.2` |
| 4 | `autotools.make(target=...)` 报“没有规则可制作目标” | `Autotools.make` 在 build_folder 执行，Makefile 在 source_folder | 配方用 `self.run("make patman", cwd=self.source_folder)` |
| 5 | 上游 `make install` 带 `install -s` | 会用构建机 strip 处理 aarch64 ELF | 不走 install 目标，`package()` 直接 copy |

## 源码修改
`patches/0001-Makefile.patch`：仅改 Makefile 4 处（版本、-march、两处 g++）。不含平台宏。

## 依赖版本
popt/1.16（静态库，制品仓已发布）。

## 验证结果
- `conan create` 通过（OHOS profile，aarch64-linux-ohos）。
- x86 runner 上动态产物无法直接运行（缺 `/lib/ld-musl-aarch64.so.1`，E544）：用同源 `.o` 静态重链的副本在 `qemu-aarch64` 下探索并确定期望输出；
  交付的动态产物本身未在 qemu 实跑，`test_package` 由 `conan create` 运行（见 test-report）。

## 注意事项
- 产物动态链接 `libc++_shared.so`、`libc.so`（NDK 默认），与仓库内其他 C++ 包一致。