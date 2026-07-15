# trio 1.16 适配笔记 (HarmonyOS PC · aarch64)

## 定位
- trio：可移植、可扩展的 `printf`/`sprintf`/`scanf` 替换库 (MIT)。
- 类型：**依赖项**（库），产出 `libtrio.a` / `libtrio.so` + 头文件 (`trio.h`、`triop.h`、`triodef.h`、`trionan.h`、`triostr.h`)。
- `package_info.libs = ["trio"]`，无外部依赖。

## 源码与版本说明
- 任务原始信息给出的 GitHub 仓库 `nathanweeks/trio`、`trio-cls/trio` 以及版本 `3.9` **均不存在**（GitHub API 全部 404，搜索无 printf 版 trio 仓库）。
- 按任务步骤 1「确认正确的仓库和最新 release tag」检索后确认：trio 官方源位于 **SourceForge** 项目 [ctrio](https://sourceforge.net/projects/ctrio/)（维护者 Daniel Stenberg / Bjorn Reese），git 仓库 `https://git.code.sf.net/p/ctrio/git`。
- 最新 release tag 为 `trio-1_16`，**版本 1.16**（2014-07-16）。本配方据此使用 1.16。
- 源码下载 URL（已验证可下载，HTTP 200，真实 gzip tarball）：
  `https://sourceforge.net/projects/ctrio/files/trio/trio-1.16.tar.gz/download`
  实测 sha256: `84d0e74f5b25f0b6c7d9b264ef41f98908e65a5056d4e75c5ef0e05d6a69fc0a`
  （按任务要求 conandata.yml 中 sha256 留空。）

## 构建系统
- **autotools**：源码包自带预生成的 `configure` 脚本（无需 autoconf）。
- 流程：`./configure` → `make` → `make install`。
- `Makefile.in`：
  - `TARGETLIB = libtrio.a`（triostr.o + trio.o + trionan.o，静态库）
  - `TARGETSHLIB = libtrio.so.2.0.0`（共享库）
  - `CFLAGS = @CFLAGS@ -I. -DDEBUG -fPIC -fvisibility=hidden`
  - `install` 同时安装 `libtrio.a`、`libtrio.so.2.0.0` 及 5 个头文件到 `libdir`/`includedir`。

## OHOS 适配要点
- **config_options**：OHOS 平台删除 `shared` 选项（仅静态库）。
- **AR 硬编码**：`Makefile.in` 中 `AR = ar`（字面量，非 `@AR@`，configure 未探测）。OHOS 交叉编译若 PATH 中无 `ar`，需替换为工具链的 `llvm-ar`（参考 jbigkit 配方做法）。
- **config.guess/config.sub**：configure 由 2014 年 autoconf 生成，可能不识别 OHOS/aarch64 目标，真机构建时或需补丁替换 config.guess/config.sub。
- 头文件 `triop.h`（私有头）会被 install，test_package 显式包含它以验证导出符号。

## test_package
- `test_package.c`：调用 `trio_snprintf(buf, sizeof(buf), "trio test: %d + %d = %d", 1, 2, 3)`，校验输出 `"trio test: 1 + 2 = 3"`。
- `CMakeLists.txt`：`find_package(trio REQUIRED CONFIG)` + `trio::trio`。
- `conanfile.py`：含 `build()` 方法，`test()` 内用 `can_run(self)` 判定后再运行测试二进制。

## 状态
**pending**（配方已生成，待真机 `conan create` 验证）。风险点：OHOS 下 `ar` 可用性、config.guess 识别。
