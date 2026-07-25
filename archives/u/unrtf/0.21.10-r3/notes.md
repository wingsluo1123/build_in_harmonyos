# unrtf 0.21.10-r3 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-07-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build unrtf 0.21.10-r3 --url=https://ftp.gnu.org/gnu/unrtf/unrtf-0.21.10.tar.gz
CI_PACKAGES=archives/u/unrtf/0.21.10-r3 zsh ci/conan/build_and_test.sh
```

Conan 配方执行：

```bash
bash ./configure --prefix=/ --datarootdir=${prefix}/share
make -j1
make install DESTDIR=<package_folder> -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config/config.guess: unable to guess system type` | 上游 2017 版 config.guess 不识别 HarmonyOS | 在 Conan 配方中构建前补充 HarmonyOS 分支，映射到 `*-linux-ohos` |
| 2 | `config.sub ... linux-ohos failed` | 上游 config.sub 不接受 `linux-ohos` | 在 Conan 配方中构建前补充 `linux-ohos*` |
| 3 | `make: jobserver mkfifo ... Operation not permitted` | HarmonyOS/HMDFS 环境限制 FIFO | 构建和安装使用 `-j1` |
| 4 | Windows/MinGW 本地编译缺少 `uint32_t` 声明 | `output.c` 使用 `uint32_t` 但未包含 `<stdint.h>` | 新增 `0002-output-include-stdint.patch` |
| 5 | OHOS/HMDFS 下直接执行 `./configure` 可能返回 `Permission denied` | 源码展开目录不保证脚本可执行 | 非 Windows 构建通过 `CONFIG_SHELL`/`bash` 调用 `configure` |
| 6 | test_package shell 脚本在真机 bash 下解析失败 | Windows CRLF 行尾导致 `pipefail\r` 被当作选项 | `test.sh` 使用 LF 行尾，并用管道校验输出 |

## 源码修改

存在 2 个持久化补丁，通过 `conandata.yml` 声明并由 `apply_conandata_patches(self)` 应用：`patches/0001-ohos-autotools-config.patch` 用于支持 HarmonyOS/linux-ohos；`patches/0002-output-include-stdint.patch` 用于补充 `output.c` 的 `<stdint.h>`。

另有 1 个构建时兼容修补：`conanfile.py` 在执行 `configure` 前将 `configure` 中创建 `confXXXXXX`/`$tmp` 临时目录的 `umask 077` 调整为 `umask 022`，用于修复 HMDFS 下 `config.status` 临时目录权限问题，避免将 autoconf 生成文件修改纳入持久化 patch。

## 依赖版本

无外部 Conan 依赖。

## 验证结果

```bash
unrtf --version
unrtf -P "$UNRTF_CONF_DIR" --text sample.rtf
```

- Windows/MinGW 预检：2026-07-24 历史记录显示 `conan create` 与 `test_package` 已通过。
- OHOS 真机定向验证：2026-07-25，run 目录 `/storage/Users/currentUser/ohos-test-runs/codex-a-unrtf-0.21.10-r3-final-20260725-165754`。
- 结果：`FINAL_RC=0`，`L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=pass`，`L4_RESULT=pass`，`L5_RESULT=pass`。
- `test_package` 实际执行 `unrtf --version`，并将 `sample.rtf` 转为 text，输出包含 `Hello HarmonyOS`。
- `L4_RESULT=pass`，补丁静态扫描无危险函数提示。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 官方 GNU 源码 URL 与 sha256 |
| test_package/conanfile.py | L1 smoke test |
| test_package/MANIFEST.yml | 测试清单 |
| commands.json | 命令行工具声明 |
---

**编译结束**: 2026-07-25
**最终状态**: built
