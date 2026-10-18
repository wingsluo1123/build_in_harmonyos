# haveged 1.9.26 适配笔记

## 环境与来源

- HarmonyOS PC aarch64；Conan 2.29.1；clang 15.0.4；Autotools。
- 上游 `v1.9.26` 源码：`https://codeload.github.com/jirka-h/haveged/tar.gz/refs/tags/v1.9.26`；SHA-256 为 `74bc6052506451ca9f23ba186f72cf81b124f859351f8a4b777ead32d9bdd4da`。
- 无外部编译依赖。生成静态 `libhavege.a`、`haveged` 命令和头文件。

## 构建与设备边界

配方对 OHOS 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，避免上游 `config.guess` 误判。HMDFS 上 configure 的私有 `umask 077` 临时目录导致 `conf*/subs1.awk: Permission denied`，构建时移除该临时目录的 umask 包裹（复用 E114）。`make check` 的 `ent/test.sh` 位于源码目录，生成的 Makefile 在独立构建目录运行；使用 `bash $(srcdir)/test.sh`，同时绕过设备缺少 `/bin/bash` 的脚本解释器路径。

`/dev/random` 的最小探针：`RNDGETENTCNT` 在 `RNDADDENTROPY` 前后均为 4038；即使以 0 位、0 字节调用 `RNDADDENTROPY`，也返回 `ENOTSUP (95)`。因此 OHOS 配置为 `--disable-daemon`，交付命令行文件/流生成器及 libhavege，不声明能够向内核熵池注入熵。探针及原始读数保存在任务工作日志；可复用机制详见 `DRAFT-haveged-1.9.26-rndaddentropy-enotsup`。

## 测试结果

`conan-verify haveged 1.9.26` 判决 `Verdict: PASS`，其中 **G1/G2/G3 通过；G4/L2/L4/L5 共 4 项未执行**（工具自身对跳过项也打印 ✅ PASS：G4 为 `⚠️ 无法找到程序包 ID` 的提前返回、从未执行产物完整性检查，L2/L4/L5 三项逐字为 `⏭️ 跳过（无 cache 路径）`；本处按实际口径如实标记为未执行，不计入通过项）。`conan create` 从干净配方编译和打包成功。

构建期间在配方 `build()` 内运行上游 `make check`：日志逐字为 `RUN: make check -j1` → `./entest -t …/ent/entitle.gif` → `Self-test good!` → `bash …/ent/test.sh` → 10 行 `Writing 16 M byte output to stdout` → `Test passed!`，即 `entest` 图像自测 1/1 与 `ent/test.sh` 的 10 个 16 MiB 随机流测试全部通过，总计 **11/11**。Conan `test_package` 从已打包的库编译、链接、调用 `havege_version/create/run/rng`，生成 32 个词并检查非全零，CTest 逐字为 `1/1 Test #1: test_haveged ..... Passed 0.24 sec` 与 `100% tests passed, 0 tests failed out of 1`，即 **1/1**。没有执行上游默认关闭的 NIST 测试；未验证内核熵注入功能。

证据：逐字读数已内联于上（`reports/` 被 `.gitignore:96` 的 `reports/` 规则排除、不进本 PR，故不以路径代替读数）。消费者源码与测试清单在 `test_package/`：`test.c`、`CMakeLists.txt`、`MANIFEST.yml`、`conanfile.py`。

## 说明

- 上游默认只启用 ENT 自测（`configure.ac` 中 `enable_enttest` 默认 `yes`）；NIST 套件默认 `no`，本适配未启用，未计入分母。
- 上游 `ent/test.sh` 在设备上改由 `bash` 执行（设备无 `/bin/bash`）；该脚本容忍至多 2 次 ENT 判失败，本次实测 0 次失败并输出 `Test passed!`。
- 内核熵注入（`RNDADDENTROPY`）未验证可用，也未声称支持；仅交付文件/流生成器与 `libhavege` API。

---

**编译结束**: 2026-10-16 23:34
**最终状态**: built
