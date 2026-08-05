# darkice 1.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published (Conan 适配完成)

## 编译步骤

1. 源码来自 GitHub rafael2k/darkice v1.6 tarball（SVN-imported仓库，源码在 darkice/trunk/ 子目录中）
2. 源码缺少 configure 脚本，只有 configure.in，需要运行 autoreconf -fi 重新生成构建系统
3. autoreconf 时需要设置 ACLOCAL_PATH 包含 pkg.m4（来自 pkg-config），否则 PKG_CHECK_MODULES 宏不会展开
4. autoconf 的 config.status 使用 umask 077 创建临时目录，在 HarmonyOS 上触发 SELinux 拒绝(E046)，需 patch 为 umask 022
5. configure 命令（Conan 管理依赖）：
   ```bash
   ./configure --prefix=$PREFIX \
     --with-vorbis --with-opus --with-flac \
     --with-lame --with-lame-prefix=$LAME_PKG_DIR \
     --without-twolame --without-pulseaudio
   ```
6. make -j1 && make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误 | SVN仓库结构导致嵌套检测选择错误子目录 | conanfile.py source() 手动提取 darkice/trunk/ 目录 |
| 2 | configure 语法错误: unexpected 'VORBIS,' | PKG_CHECK_MODULES宏未展开（aclocal.m4缺少pkg.m4） | 设置ACLOCAL_PATH包含pkg.m4路径后重新运行autoreconf -fi |
| 3 | config.status: Permission denied | autoconf使用umask 077创建临时目录，SELinux拒绝写入 | patch configure脚本将umask 077改为umask 022 |
| 4 | BadZipFile: File is not a zip file | GitHub tarball API URL缺少.tar.gz扩展名，conan误判为zip | conandata.yml添加filename: "darkice-1.6.tar.gz" |
| 5 | libogg版本冲突 | flac/1.4.3需要1.3.5，libvorbis/1.3.7需要1.3.6 | 使用override=True强制使用libogg/1.3.6 |
| 6 | alsa-lib conan配方topology链接错误 | snd_lib_log未定义 | 暂用系统cmd-pkg替代alsa-lib conan依赖 |
| 7 | lame/faac使用LA_SEARCH_LIB而非pkg-config | darkice自定义检测宏 | 传递--with-lame-prefix指向conan依赖包目录 |

## 依赖版本

### Conan 管理依赖
- libogg/1.3.6 (override=True 解决版本冲突)
- libvorbis/1.3.7
- opus/1.5.2.1
- flac/1.4.3
- lame/4.0

### 系统依赖 (cmd-pkg, auto-detected via pkg-config)
- alsa-lib 1.2.12
- faac 1.40
- fdk-aac 2.0.3
- jack 1.9.22
- libsamplerate 0.2.2

### 不可用依赖 (已禁用)
- twolame: 制品仓和cmd-pkgs均不可用
- pulseaudio: 制品仓和cmd-pkgs均不可用

## 验证结果

```bash
$ darkice -h
DarkIce 1.6 live audio streamer, http://code.google.com/p/darkice/
Copyright (c) 2000-2007, Tyrell Hungary, http://tyrell.hu/
Copyright (c) 2008-2013, Akos Maroy and Rafael Diniz
Copyright (c) 2014-2024, Rafael Diniz and others
```

## Conan 配方

- conanfile.py: application 类型，使用 Autotools 工具链
- conandata.yml: 包含源码URL和sha256，无补丁
- test_package/: 执行 darkice -h 冒烟测试
- commands.json: 声明为命令行工具 (R38)

## 注意事项

- darkice是音频流工具，运行需要至少一个音频输入源（ALSA/OSS/PulseAudio/JACK）
- 此仓库为SVN导入结构，源码在 darkice/trunk/ 子目录中
- autoreconf需要pkg.m4宏才能正确展开PKG_CHECK_MODULES
- twolame和pulseaudio在制品仓和cmd-pkgs中均不可用，已禁用
- alsa-lib conan配方有topology模块链接错误，暂用系统cmd-pkg替代

**编译结束**: 2026-08-06 06:22
**最终状态**: published (Conan 适配)
