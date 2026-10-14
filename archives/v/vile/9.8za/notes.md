# vile 9.8za 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-10-01
- 编译器: OHOS SDK clang 15.0.4
- 目标: aarch64-linux-ohos
- 状态: built（本地 conan create / conan-verify 通过，未上传）

## 上游确认
- 任务名: vileC++
- 包名: vile
- 上游版本: 9.8za
- 上游主页: https://invisible-island.net/vile/
- 源码 URL: https://invisible-island.net/archives/vile/current/vile-9.8za.tgz
- SHA256: 65ba15ec145dfc5506217162228c7d88f01c0490a0dccde7a8a19f1c7c1b93b2
- `C++` 是任务语言标注，不是包名；`vile` 主体为 C，带少量 C++/Perl 辅助源码。

## 编译步骤
1. 依赖预检：`ncurses/6.6`、`flex/2.6.4` 已在 ohpcd 制品仓发布。
2. 语言预检：任务 `cpp`，检测 `cpp`，主体 C/C++ 占比 76%。
3. Conan 构建：
   - `--prefix=/`
   - `--build=aarch64-unknown-linux-gnu`
   - `--host=aarch64-unknown-linux-ohos`
   - `--with-screen=ncursesw`
   - `--disable-rpath-hack`
   - `make -j1`
   - `make check`
4. 打包：`make install -j1`，复制 `COPYING` 到 `licenses/`。

## 上游测试清点
- `make check` 输出：`Sorry, no batch tests available.`
- 源码中有 `test_io.c`、`test_btree`/`test_regexp` 调试驱动和插件示例，但未接入任何批量 runner。
- 上游正式自动化测试数：0。
- 本地原生构建实测 `vile -V` 输出 `vile version 9.8za`。

## 适配后测试
- `test_package/test.sh`：2 个功能检查项
  - F1: `vile -V` 输出版本 `9.8za`
  - F2: `vile -x` 输出 usage
- `test_package/ohos_abi_check.py`：3 个鸿蒙特有检查项
  - A1: ELF64 + `EM_AARCH64`
  - A2: `.interp == /lib/ld-musl-aarch64.so.1`
  - A3: `DT_NEEDED` 不含共享 `libncurses`
- 合计 5 个独立检查项，计数口径为独立检查项数量。

## 验证结果
- `conan-verify vile 9.8za --profile ohos-local`: PASS
- G1: PASS
- G2: PASS
- G3: PASS
- G4: PASS
- L2/L4/L5: PASS
- ABI 检查：3/3 通过
- `finish vile 9.8za built`: W3 本地 CI 模拟通过，`.ci-result.json` exit_code=0
- 本地首次 W3 因仓库既有无关 junk 文件失败；使用本机 `ohos-local` profile 的临时项目根重跑后通过，未修改仓库框架文件。

## 依赖版本
- ncurses/6.6
- flex/2.6.4

## 源码修改
无上游源码补丁。上游 `config.sub` 已支持 `aarch64-unknown-linux-ohos`。
构建时对 `configure` / `config.guess` 做最小修正：
- 将两处 `case `$ac_config_guess`` 改为 `case $host_os`，避免在 HarmonyOS 上触发 `config.guess` 的临时目录探测；
- 将 Autoconf 临时目录创建从 `umask 077` 放宽为 `umask 022`，避免 CI 环境下 `config.status` 写临时文件被拒。

## 注意事项
- `--disable-rpath-hack` 用于避免 Conan cache 绝对路径进入 `RUNPATH`。
- 本地交叉环境不执行 runtime smoke，`test_package` 中 ABI 检查仍会真实执行。
- 2026-10-02 追加 CI 修复：HarmonyOS worker 上 `config.guess` / `config.status` 的临时目录权限问题已通过 recipe 内最小修正解决；本地 `conan-verify vile 9.8za --profile ohos-local` 重新通过。
- 2026-10-14 追加 CI 修复：HarmonyOS worker 的 make 未按 `filters/makefile` 的 `VPATH` 解析上游 `filters/*.c`，导致 #89209 报 `No rule to make target 'atr2ansi.o'`。recipe 现在在 configure 前将 `filters` 源文件同步到 `build-release/filters`；本地 `conan create . -pr:h=ohos-local -pr:b=ohos-local --build=missing` 已重新通过。
- 2026-10-14 追加 CI 修复：CI 的 `config.status` 曾把 `filters/makefile` 的 `srcdir` 生成为乱码路径，导致 `make install` 找不到 `filters.rc`。recipe 现在在 configure 后显式修正 `VPATH/top_srcdir/srcdir`；本地 `conan create` 与安装阶段再次通过。
- 2026-10-14 追加测试修复：`vile -x` 的 usage 输出在 stderr，而 F2 原脚本只捕获 stdout；`test.sh` 已改为 `2>&1` 捕获，断言本身保持不变。
---

**编译结束**: 2026-10-01 02:37
**最终状态**: built
