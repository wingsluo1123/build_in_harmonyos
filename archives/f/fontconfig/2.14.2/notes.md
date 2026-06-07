# fontconfig 2.14.2 编译笔记

## 编译日期
2026-05-26

## 版本信息
- 源码版本: 2.14.2
- pkg-config 版本: 2.14.2
- 构建系统: Meson (autotools 在 HMDFS 上有临时文件权限问题)

## 编译状态
built (编译成功，未发布)

## 安装路径
- 库文件: ~/usr/local/lib/libfontconfig.so.1.13.0 (1.6MB)
- pkg-config: ~/usr/local/lib/pkgconfig/fontconfig.pc
- 头文件: ~/usr/local/include/fontconfig/
- 配置文件: ~/usr/local/etc/fonts/fonts.conf

## 依赖情况
- **freetype2**: ✅ 已安装 (26.1.20)
- **expat**: ✅ 已安装 (2.6.0) - 需要先编译
- **zlib**: ✅ 已安装 (作为 freetype2 依赖)

## 编译流程

### 1. 下载源码
使用 ohc-run.py init-build fontconfig 2.14.2 --url="https://www.freedesktop.org/software/fontconfig/release/fontconfig-2.14.2.tar.gz"

### 2. 配置阶段遇到的问题

#### 问题 1: E007 - config.guess 无法识别 HarmonyOS
**症状**:
```
checking build system type... ./config.guess[1729]: can't create /storage/Users/currentUser/tmp/cgagfKkg/dummy.c: Permission denied
config.guess: unable to guess system type
```

**解决方案**:
复制已成功编译的软件（如 pkgconf）的更新版本：
```bash
cp /storage/Users/currentUser/tmp/builds/pkgconf-2.5.1.work/config.guess .
cp /storage/Users/currentUser/tmp/builds/pkgconf-2.5.1.work/config.sub .
```

#### 问题 2: HMDFS 临时文件权限问题 (autotools)
**症状**:
```
./config.status[1143]: can't create ./confHlgJfJ/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**: HMDFS 文件系统不支持在源码目录下创建临时目录，即使设置 TMPDIR 也无效

**解决方案**: 切换到 Meson 构建系统

#### 问题 3: 缺少 expat 依赖
**症状**:
```
checking for EXPAT... no
checking for expat.h... no
configure: error: *** expat is required. or try to use --enable-libxml2
```

**解决方案**:
先编译 expat 2.6.0（使用 CMake，因为 autotools 有同样的 HMDFS 问题）：
```bash
cd ~/tmp/builds/expat-2.6.0.work/build
cmake .. -DCMAKE_INSTALL_PREFIX=~/usr/local -DCMAKE_BUILD_TYPE=Release
make -j4 && make install
```

#### 问题 4: Meson 无法检测编译器
**症状**:
```
meson.build:1:0: ERROR: Unknown compiler(s): [['clang']]
Running `clang --version` gave "[Errno 2] No such file or directory: 'clang'"
```

**解决方案**:
创建 native.ini 文件指定编译器路径：
```ini
[binaries]
c = '/data/service/hnp/bin/clang'
cpp = '/data/service/hnp/bin/clang++'
ar = '/data/service/hnp/bin/llvm-ar'
strip = '/data/service/hnp/bin/llvm-strip'
pkgconfig = '/data/service/hnp/bin/pkg-config'

[properties]
c_args = ['-I/storage/Users/currentUser/usr/local/include', '-fPIC', '-O2']
cpp_args = ['-I/storage/Users/currentUser/usr/local/include', '-fPIC', '-O2']
c_link_args = ['-L/storage/Users/currentUser/usr/local/lib']
cpp_link_args = ['-L/storage/Users/currentUser/usr/local/lib']
```

#### 问题 5: Meson 无法检测 Ninja
**症状**:
```
ERROR: Could not detect Ninja v1.8.2 or newer
```

**根因**: Python subprocess 无法执行未签名的 ELF 文件

**解决方案**:
使用 SKILL 提供的 sign-elf 工具签名 ninja：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/bin/ninja
```

#### 问题 6: Python 脚本无法直接执行
**症状**:
```
FAILED: [code=126] fc-case/fccase.h
/bin/sh: /storage/Users/currentUser/tmp/builds/fontconfig-2.14.2.work/fc-case/fc-case.py: Permission denied
```

**根因**: HarmonyOS 安全机制阻止直接执行 Python 脚本

**解决方案**:
修改多个 meson.build 文件，使用 python3 执行脚本：

- fc-case/meson.build:
```meson
command: [find_program('python3'), files('fc-case.py'), '@INPUT0@', ...]
```

- fc-lang/meson.build:
```meson
command: [find_program('python3'), files('fc-lang.py'), orth_files, ...]
```

- conf.d/meson.build:
```meson
command: [find_program('python3'), files('write-35-lang-normalize-conf.py'), ...]
```

- doc/meson.build:
```meson
extract_man_list_cmd = find_program('python3')
man_list = run_command(extract_man_list_cmd, files('extract-man-list.py'), fncs_files, check: true).stdout().split()
```

#### 问题 7: 安装后缺少 symlinks
**症状**:
```
Symlink creation does not work on this platform. Skipping all symlinking.
```

**解决方案**:
手动创建 symlinks：
```bash
cd ~/usr/local/lib
ln -s libfontconfig.so.1.13.0 libfontconfig.so.1
ln -s libfontconfig.so.1 libfontconfig.so
```

### 3. 编译和安装
```bash
cd ~/tmp/fontconfig-build
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export PATH=/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH
meson setup . ~/tmp/builds/fontconfig-2.14.2.work --prefix=~/usr/local --native-file ~/tmp/builds/fontconfig-2.14.2.work/native.ini
ninja -j4
ninja install
```

## pkg-config 验证
```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion fontconfig
# 输出: 2.14.2
pkg-config --cflags fontconfig
# 输出: -I/storage/Users/currentUser/usr/local/include -I/storage/Users/currentUser/usr/local/include/freetype2
pkg-config --libs fontconfig
# 输出: -L/storage/Users/currentUser/usr/local/lib -lfontconfig -lfreetype -lz
```

## 关键发现

### 1. 构建系统选择
fontconfig 支持三种构建系统:
- autotools (./configure) - **在 HMDFS 上不可用**
- Meson (推荐) - **可行，但需要 workaround**
- CMake (不支持)

在 HMDFS 文件系统上，autotools 有临时文件权限问题，Meson 是唯一可行的选择。

### 2. HarmonyOS Python 执行限制
Python subprocess 和 shell 都无法直接执行 Python 脚本文件。必须使用 `python3 script.py` 方式。

### 3. ELF 签名的重要性
所有编译相关的可执行文件（ninja、clang、python 等）都必须签名才能执行。

### 4. Meson native.ini 文件
对于 HarmonyOS，必须使用 native.ini 文件明确指定编译器路径，否则 Meson 无法检测编译器。

## 修改的文件列表
- fc-case/meson.build - 修改 Python 脚本执行方式
- fc-lang/meson.build - 修改 Python 脚本执行方式
- conf.d/meson.build - 修改 Python 脚本执行方式
- doc/meson.build - 修改 Python 脚本执行方式
- config.guess - 替换为更新版本
- config.sub - 替换为更新版本

## 后续建议

1. **发布预编译包**: 需要制作 tar.gz 预编译包并签名
2. **改进 Meson 补丁**: 建议创建统一的 Meson Python 脚本执行 patch
3. **文档构建**: doc 部分未完全构建（缺少 docbook 工具），但不影响核心功能

---
*编译笔记结束*
---

**编译结束**: 2026-05-26 14:30
**最终状态**: built
---

**编译结束**: 2026-05-26 14:31
**最终状态**: built
