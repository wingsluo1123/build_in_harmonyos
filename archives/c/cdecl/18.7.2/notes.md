# cdecl 18.7.2 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 执行适配前依赖预检：`bash ci/scripts/preflight_check.sh cdecl/18.7.2`，无依赖。
2. 初始化源码与归档：`python3 scripts/ohc-run.py init-build cdecl 18.7.2 --url=https://github.com/paul-j-lucas/cdecl/releases/download/cdecl-18.7.2/cdecl-18.7.2.tar.gz`。
3. 修复 `configure` 中 `umask 077` 为 `umask 022`，解决 HMDFS 临时目录写入问题。
4. 配置构建：`./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --disable-dependency-tracking --without-readline --disable-term-size`。
5. 使用 `make -j1` 编译，`make install DESTDIR=$TEST_PREFIX` 安装验证。
6. 生成 Conan 配方并按命令行工具标准修正 package_info、commands.json 与 test_package。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法猜测 build type | config.guess 在 HarmonyOS 上创建临时文件失败且不识别系统 | 显式传入 `--build/--host=aarch64-unknown-linux-ohos` |
| 2 | 缺少 readline.h | readline 仅用于交互增强，环境中未提供头文件 | 添加 `--without-readline` |
| 3 | 缺少 curses 库 | 终端尺寸功能依赖 curses，批处理功能不需要 | 添加 `--disable-term-size` |
| 4 | config.status 写入 `subs1.awk` 权限失败 | HMDFS 下 `umask 077` 创建的临时目录不可写 | 补丁改为 `umask 022` |
| 5 | GNU make jobserver mkfifo 警告 | HMDFS 不支持 mkfifo | Conan 构建使用 `make -j1` |

## 源码修改

- `patches/0001-configure-umask.patch`: 将 `configure` 临时目录创建处的 `umask 077` 改为 `umask 022`。

## 依赖版本

无 Conan 依赖。`readline`/`curses` 可选功能已禁用。

## 验证结果

```bash
$ cdecl --version
cdecl 18.7.2

$ printf 'declare x as pointer to int\n' | cdecl
int *x;
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方，应用补丁并构建 cdecl CLI |
| conandata.yml | 官方源码 URL、sha256 与补丁声明 |
| patches/0001-configure-umask.patch | HMDFS 权限兼容补丁 |
| test_package/test_cdecl.sh | 消费者侧命令行功能验证 |
| commands.json | hicmd 命令行工具声明 |

## 注意事项

- cdecl 是命令行工具，不应声明 `cpp_info.libs`。
- `readline`/`curses` 禁用后不影响非交互式声明解释与生成能力。
---

**编译结束**: 2026-07-15 10:34
**最终状态**: built
