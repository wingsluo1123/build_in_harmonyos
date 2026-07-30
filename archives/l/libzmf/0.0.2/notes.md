# libzmf 0.0.2 适配笔记

## 编译环境
- 构建系统: autotools (upstream release tarball ships pre-generated `configure`)
- 编译日期: 2026-07-30
- 编译器: clang/clang++ (OHOS aarch64 toolchain)
- 状态: published

## 编译步骤

```bash
# 1. 解压上游 release tarball (含预生成 configure，无需 autoreconf)
# 2. 应用补丁：替换 config.guess/config.sub 为 OHOS-aware 版本
# 3. 修正 generated configure 的 umask 077 -> 022 (HarmonyOS FS 限制)
# 4. 配置 (静态库，DevBox 兼容)
sh ./configure --prefix=$PREFIX --enable-static --disable-shared
# 5. 编译
make -j2
# 6. 安装到 staging
make install DESTDIR=$STAGING
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 OHOS aarch64 | 上游 release tarball 的 autotools 文件旧 | 补丁替换为 OHOS-aware 版本 |
| 2 | configure 执行报 "bad interpreter: Permission denied" | OHOS 文件系统对 shebang `/bin/sh` 限制 | 用 `sh ./configure` 调用绕过 |
| 3 | 生成文件权限异常 (umask 077) | HarmonyOS FS 对受限组权限目录无法创建文件 | configure 内 `umask 077` -> `umask 022` |

## 源码修改

补丁仅替换 config.guess/config.sub（平台识别），不修改 libzmf 业务源码。
上游 configure 脚本已预生成，无需 autoreconf/automake/libtoolize。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| librevenge | 0.0.5 | @ohpcd/stable (核心依赖) |
| boost | 1.84.0 | @ohpcd/stable (header-only) |
| zlib | 1.3.1 | @ohpcd/stable |
| libpng | 1.6.43 | @ohpcd/stable |
| icu | 73.2 | @ohpcd/stable |

## 验证结果

```bash
# conan create 验证 (W3 本地编译验证)
conan create archives/l/libzmf/0.0.2 --name=libzmf --version=0.0.2
# test_package L1 测试
conan test archives/l/libzmf/0.0.2/test_package libzmf/0.0.2
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (autotools + 静态库) |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| test_package/ | L1 测试 (调用 ZMFDocument API) |
| patches/0001-config.guess.patch | OHOS-aware config.guess |
| patches/0002-config.sub.patch | OHOS-aware config.sub |

## 注意事项

- libzmf 0.0.2 的上游 release tarball 已预生成 configure，正常情况下
  无需 autoreconf。仅当补丁修改 configure.ac/Makefile.am 时才需要重新生成。
- 依赖 librevenge/0.0.5 必须先发布到 @ohpcd/stable (R36: 依赖发布优先级)。
