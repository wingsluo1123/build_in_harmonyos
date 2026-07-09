# Notes — zangband 2.7.5.1

## 基本信息
- **软件**: zangband (Roguelike computer role playing game based on Angband)
- **版本**: 2.7.5.1 (2.7.5pre1)
- **构建系统**: autotools (autoconf 2.59)
- **源码**: SourceForge release tarball (zangband-2.7.5pre1.tar.gz)

## 编译过程

### Phase 1: 下载与初始化
- 从 SourceForge 下载 release tarball: zangband-2.7.5pre1.tar.gz (2.7MB)
- URL: https://sourceforge.net/projects/zangband/files/zangband-src/2.7.5%20preview%20I/zangband-2.7.5pre1.tar.gz/download
- init-build 成功，环境检查通过

### Phase 2: Configure
- 构建系统: autotools (configure + makefile.in + makefile.zb)
- configure 参数: `--prefix=$DEFAULT_PREFIX`
- CFLAGS: `-fPIC -O2 -I$DEFAULT_PREFIX/include`
- LDFLAGS: `-L$DEFAULT_PREFIX/lib`
- **问题1 (E011)**: configure/config.status 使用 `umask 077` 创建临时目录，导致 HMDFS 权限拒绝
  - **解决**: sed 修改 umask 077 → umask 022 (configure 和 config.status)
- **问题2**: make 触发 configure 重建（.version 依赖链），aclocal 失败
  - **解决**: 创建 .version 文件并 touch 时间戳

### Phase 3: Make
- 编译命令: `make V=1 -j1`
- 成功编译所有源文件（lua/tolua → l-*.c wrappers → object files → zangband binary）
- 1 warning: zborg3.c logical-not-parentheses (非致命)
- 链接: -lz -lncurses -lX11

### Phase 4: Install
- **问题**: makefile 的 DESTDIR 变量是游戏数据路径，不是标准 staging 前缀
- **解决**: 使用 `make install prefix=$TEST_PREFIX/$DEFAULT_PREFIX GAMEGROUP=` 覆盖 prefix
- Staging 安装成功: binary + data files
- $DEFAULT_PREFIX 安装成功: binary 可执行

### Phase 5: Test
- 无 `make check` 目标（makefile 不提供）
- `make test` 仅打印信息，不是测试套件
- 二进制验证: file 确认 ELF 64-bit arm64, 运行 exit code 0

### Phase 6: Package
- 预编译包: zangband-2.7.5.1-ohos-aarch64.tar.gz (6.8MB)
- 包含: bin/zangband + share/games/zangband/ (data files)

## 依赖处理
- ncurses: 已预编译安装 ($DEFAULT_PREFIX/lib/libncurses.a)
- zlib: 已预编译安装 ($DEFAULT_PREFIX/lib/libz.a)
- X11: 已预编译安装 ($DEFAULT_PREFIX/lib/libX11.so)

## 补丁
- 0001-configure.patch: umask 077 → 022 (E011 HMDFS 权限修复)

## 知识积累

### E011: umask 077 导致 HMDFS 权限问题
- **现象**: configure/config.status 使用 `umask 077` 创建临时目录, HMDFS 上 Permission denied
- **根因**: HMDFS UID 映射机制导致 0700 权限目录对当前进程不可写
- **解决**: sed 修改 umask 077 → umask 022
- **影响**: 所有 autotools 项目在 HMDFS 上 configure 时均会遇到

### E001: 编译器未找到 (CC=clang)
- **现象**: configure 找不到 `cc` 编译器
- **根因**: 平台无 `cc` 软链接, 只有 `clang` 可用
- **解决**: 设置 `CC=clang` 环境变量
- **影响**: 所有 autotools 项目

### E076: HMDFS FIFO 限制
- **现象**: `make -j20` 触发 `jobserver mkfifo: Operation not permitted`
- **根因**: 鸿蒙内核对非文件 fd 的 fstat/lseek 返回 EACCES
- **解决**: 使用 `make -j1` 避免并行构建的 FIFO 通信
- **影响**: 所有使用 GNU make 并行构建的项目

### 非标准 DESTDIR 用法
- **现象**: zangband makefile 的 DESTDIR 变量是游戏数据路径, 不是标准 staging 前缀
- **解决**: 使用 `prefix=` 覆盖而非 `DESTDIR=` 进行 staging 安装
- **影响**: 仅 zangband 特有

### Conan 配方适配
- **SourceForge 重定向**: conan `get()` 无法处理, 使用 `exports` 导出本地 tarball
- **CC_AUX 硬编码**: configure 生成的 makefile 中 `CC_AUX := gcc`, 需 make 命令行覆盖
- **TK_PORT**: configure 检测到 Tk 但平台无 tk.h, 需 `TK_PORT=` 禁用
- **autoconf.h 路径**: 需 `-Isrc` 或绝对路径 include
- **.version 依赖链**: 需创建 stub 文件 + `-o` 标志跳过自动重建

---
**编译结束**: 2026-06-26
**最终状态**: built
---

**编译结束**: 2026-06-26 10:07
**最终状态**: built
