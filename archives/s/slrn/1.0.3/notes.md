# slrn 1.0.3 适配笔记

## 编译环境
- 构建系统: autotools（上游 2016 年预生成 configure，autoconf 2.69 世代）
- 编译日期: 2026-10-01
- 编译器: OHOS SDK clang 15（--target=aarch64-linux-ohos，musl sysroot）
- 状态: built（W3 conan create 通过后升级 published）

## 上游版本说明

上游没有名为 "1.0.3" 的发布包；jedsoft.org 官方发布的 1.0.3 系列制品是
`slrn-1.0.3a.tar.bz2`（1.0.3 的 respin），即本配方下载的源码。
SHA256: 3ba8a4d549201640f2b82d53fb1bec1250f908052a7983f0061c983c634c2dac

## 测试计数口径

统一口径：**独立检查项数量**（每个检查项单独执行、单独按退出码/输出断言判定）。

- 上游测试：0。证据：`make check` -> "No rule to make target `check'"；
  src/Makefile.in 与顶层 Makefile 均无 test/check 目标；源码树无 tests/ 目录。
- 适配后新增测试：8 项 = 消费者 CLI 契约 5 项（test_slrn.sh）
  + 鸿蒙特有 3 项（ohos_slrn_test.sh），详见 test_package/MANIFEST.yml。

## 编译步骤

```bash
./configure --host=aarch64-linux-ohos --build=aarch64-linux-ohos \
  --prefix=<prefix> \
  --with-slang=<slang 包路径> --with-ssl=<openssl 包路径> \
  slrn_cv_va_copy=yes slrn_cv___va_copy=yes slrn_cv_va_val_copy=no
make -j            # 交叉编译时附加 SKIP_CHKSLANG=1
make install DESTDIR=<package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 拒绝 aarch64-linux-ohos | 自带 config.sub 为 2014 版，不识别 linux-ohos | 补丁 0001：两条 canonicalization 路径均加 linux-ohos* |
| 2 | configure 报 "cannot run test program while cross compiling" | va_copy/__va_copy/va_list 按值复制三个 AC_TRY_RUN 无交叉默认值 | 预置 slrn_cv_va_copy=yes、slrn_cv___va_copy=yes、slrn_cv_va_val_copy=no（aarch64 上 va_list 是数组类型，不能按值赋值） |
| 3 | make 报 "chkslang: cannot execute binary file" (Error 126) | src/Makefile.in 的 slangversion 目标构建并立即运行目标端 chkslang | 补丁 0003：SKIP_CHKSLANG=1 时跳过运行；交叉编译由配方传入，OHOS CI 原生构建仍执行 chkslang；slang>=2.2.3 由 conan 依赖 slang/2.3.3 锁定 |
| 4 | （预防）CI 上 config.status 临时目录不可写 | HMDFS 属主映射使 umask 077 的 0700 目录对构建进程不可写（知识 E011） | 补丁 0002：configure 中 6 处 umask 077 → 022 |
| 5 | CI 上 slrn --show-config 报 "Unable to locate slrn.sl on load path"（--prefix=/ 固化为 //share/slrn/slang） | conan 打包 prefix=/ 使编译期 SLRN_SLANG_DIR 在消费机不存在（E317 同族：prefix=/ 资源路径固化） | package_info() 用上游官方环境变量覆盖：runenv_info.define("SLRN_SLANG_DIR", <包内 share/slrn/slang>) |
| 6 | CI 上 uname 报 "HarmonyOS" 而非 "OpenHarmony" | HarmonyOS PC 的 uname sysname 是 HarmonyOS | 鸿蒙测试 check1 兼容 OpenHarmony/HarmonyOS 两种命名 |

## 源码修改

- `autoconf/config.sub`：识别 linux-ohos（补丁 0001）
- `src/Makefile.in`：slangversion 目标增加 SKIP_CHKSLANG 守卫（补丁 0003）
- `configure`：umask 077 → 022（补丁 0002）

无 `__OHOS__` 平台宏注入（R8/PF5 合规），全部为通用可移植性修改。

## 依赖版本

- slang/2.3.3（制品仓已发布，必须）
- openssl/3.0.16（制品仓已发布，SSL 支持）
- uudeview、canlock：制品仓未发布，保持禁用（slrn 内置 yEnc 解码；canlock 仅用于 Cancel-Lock 发帖）

## 发现与知识

- ✅ chkslang 类构建期目标端校验工具交叉守卫 → DRAFT-slrn-1.0.3-build-time-target-tool-run-guard（.kv+.md 配对，撞库：E359/E543 未覆盖纯校验可跳过形态）
- ✅ conan --prefix=/ 固化资源目录的上游环境变量 runenv 覆盖 → DRAFT-slrn-1.0.3-runenv-override-prefix-root-resource-dir（.kv+.md 配对，撞库：E317 同族零补丁变体）
- ✅ 既有知识复用：E011（HMDFS umask）、E543（AC_TRY_RUN 交叉预置）、E359（构建期工具宿主编译器映射，评估后判定不适用本场景）

## 验证结果

- 探索性交叉编译（macOS → aarch64-linux-ohos）：configure/make/make install 全部通过，
  产物 `src/objs/slrn` 为 ELF aarch64 musl 动态链接可执行文件
- `make check`：无目标（上游 0 测试，已记录）
- W3 conan create：见 reports/ 与 .ci-result.json（finish 自动生成）
- 鸿蒙特有测试 3 项在 HarmonyOS PC（CI）实跑：uname 报 OpenHarmony/HarmonyOS、
  libslang.so.2 运行时版本 2.3.3、$TMPDIR(HMDFS) 中 init 文件经 S-Lang 引擎生效（CI #65953 实测 8 项中 7 项通过；check3 初版暴露 SLRN_SLANG_DIR 固化路径问题，修复后复验）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/slrn | 新闻阅读器主程序 |
| share/slrn/slang/*.sl | S-Lang 脚本扩展 |
| share/man/man1/slrn.1 | man 手册 |
| share/doc/slrn/ | 上游文档 |

## 注意事项

- metamail 集成（默认关闭）在 mime.c 中硬编码 /tmp；HarmonyOS PC 的 /tmp 只读（E002）。
  本适配未修改该路径：该功能默认禁用且 metamail 本身未适配 OHOS。
  其余临时文件路径（slrn_open_tmpfile）已遵循 TMP/TMPDIR 环境变量。
- 交互式界面需要可用终端（TERM）；test_package 中已设置 TERM/HOME 兜底。
---

**编译结束**: 2026-10-01 02:32
**最终状态**: built
