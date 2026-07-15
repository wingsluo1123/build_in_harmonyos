# lhasa 0.6.0 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build lhasa 0.6.0 \
  --url=https://github.com/fragglet/lhasa/releases/download/v0.6.0/lhasa-0.6.0.tar.gz --force

source .build-context-lhasa-0.6.0
cd "$BUILD_SRC_DIR"
# OHOS/HMDFS 临时目录权限修复；Conan recipe 中由 _fix_umask() 自动执行。
sed -i 's/umask 077/umask 022/g' configure
TMPDIR="$REPO_DIR/.tmp-build" PATH="$HOME/usr/local/bin:$PATH" \
  sh ./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  --prefix="$DEFAULT_PREFIX" --disable-shared --enable-static
TMPDIR="$REPO_DIR/.tmp-build" PATH="$HOME/usr/local/bin:$PATH" make -j1
TMPDIR="$REPO_DIR/.tmp-build" PATH="$HOME/usr/local/bin:$PATH" \
  make install DESTDIR="$TEST_PREFIX"
```

实际产物包含 `bin/lha`、`lib/liblhasa.a`、`include/liblhasa-0.6.0/*.h`、`lib/pkgconfig/liblhasa.pc`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 无法识别 HarmonyOS | 上游 config.guess 对 `uname -s = HarmonyOS` 无匹配 | 显式传入 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos` |
| 2 | `config.status: could not setup config files machinery` | Autoconf 使用 `umask 077` 创建临时目录，OHOS/HMDFS 权限导致后续文件写入失败 | 构建前将 `configure`/`config.status` 中 `umask 077` 替换为 `umask 022` |
| 3 | GNU make jobserver FIFO 报 `Operation not permitted` | OHOS 当前文件系统不支持 jobserver mkfifo | 使用 `make -j1` |
| 4 | 一键 build 自动重试将 `curl -fsSL ...` 误传入 configure/make | 自动重试命令串被构建驱动解析异常 | 改用手动探索验证，并在 Conan recipe 中固化稳定构建逻辑 |

## 源码修改

无持久源码补丁。Conan recipe 在 `build()` 阶段运行 `_fix_umask()` 修改构建目录中的生成脚本，避免记录生成文件 patch。

## 依赖版本

无外部 Conan 依赖。

## 验证结果

```bash
# 手动探索验证
sh ./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  --prefix=$DEFAULT_PREFIX --disable-shared --enable-static
make -j1
make install DESTDIR=$TEST_PREFIX
# 结果: configure / make / install 均通过，安装出 lha 与 liblhasa.a。

# Conan 验证
python3 scripts/ohc-run.py conan-verify lhasa 0.6.0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 Autotools 配方，包含 OHOS 平台校验与 umask 修复 |
| conandata.yml | 官方 GitHub release 源码 URL 与 sha256 |
| test_package/test.c | 消费者视角链接 liblhasa 并调用公开 API |
| test_package/conanfile.py | 执行 CMake 消费者测试并运行 `lha`（无参数，验证退出码 255） |
| commands.json | 命令行工具 `lha` 的 hicmd 声明 |

## 注意事项

- `lhasa` 同时提供库和命令行工具；R38 要求软件级目录必须有 `commands.json`。
- 上游 `make check` 是归档回归套件，探索阶段可在本机运行；Conan `test_package` 使用 API + CLI 烟雾测试保持验证稳定。
