# lowdown 3.0.1 编译记录

## 编译开始
**时间**: 2026-07-13  
**软件**: lowdown  
**版本**: 3.0.1  
**构建系统**: oconfigure（自定义 configure，KEY=value 语法）

## 步骤记录

### Step 1: init-build
- ✅ 下载源码（GitHub release tarball: VERSION_3_0_1）
- ✅ 解压创建 .orig 和 .work 目录
- ✅ 环境检查通过（clang 15.0.4, make 4.4.1, cmake 4.1.2）

### Step 2: configure
- ✅ oconfigure 使用 KEY=value 语法：`./configure CC=clang PREFIX=/usr/local`
- ✅ 成功检测所有依赖函数和头文件
- ⚠️ mktemp 缺失（E002: /tmp 只读），使用 busybox mktemp 替代

### Step 3: make
- ✅ 所有 .o 文件编译成功（24 个源文件）
- ✅ liblowdown.a 静态库创建成功（1.3MB）
- ✅ lowdown 二进制链接成功（875KB）
- ⚠️ HMDFS 不支持硬链接（E079），使用 cp 替代 ln 创建 lowdown-diff

### Step 4: make install (DESTDIR)
- ✅ 二进制安装到 staging/bin: lowdown, lowdown-diff
- ✅ 库文件安装到 staging/lib: liblowdown.a
- ✅ 头文件安装到 staging/include: lowdown.h
- ✅ pkg-config 文件安装到 staging/lib/pkgconfig: lowdown.pc
- ✅ man 手册安装（.1/.3/.5 共 34 个文件）
- ✅ 共享模板安装（html/latex/man/ms/odt 共 6 个文件）

### Step 5: 验证
- ✅ 二进制存在: lowdown (875KB), lowdown-diff (875KB)
- ✅ 库文件存在: liblowdown.a (1.3MB)
- ✅ 头文件存在: lowdown.h
- ✅ 基本功能验证: lowdown -t term / -t html 输出正确
- ⚠️ 回归测试（make regress）因 HMDFS 硬链接限制跳过

## 问题与修复

### 问题1: configure 报 mktemp 不可用
- **现象**: `mktemp: inaccessible or not found`
- **原因**: OHOS 环境缺少 mktemp 命令（E002）
- **修复**: 使用 `/data/service/hnp/bin/busybox mktemp` 替代

### 问题2: configure 不支持 --prefix 参数
- **现象**: `option not recognised`
- **原因**: oconfigure 使用 `KEY=value` 语法而非 `--key=value`
- **修复**: 使用 `CC=clang PREFIX=/path` 格式传参

### 问题3: Makefile 使用 BSD make 语法
- **现象**: `missing separator`（GNU make 不兼容）
- **原因**: 原 Makefile 使用 `.ifdef`/`.endif` BSD make 语法
- **修复**: 自动转换为 GNU make 语法（`ifdef`/`endif`）

### 问题4: HMDFS 不支持硬链接
- **现象**: `ln: cannot create hard link`
- **原因**: HMDFS 文件系统限制（E079）
- **修复**: 使用 `cp -f` 替代 `ln -f`

### 问题5: sed 命令不可用
- **现象**: lowdown.pc 生成失败
- **原因**: OHOS 环境缺少 sed 命令
- **修复**: 使用 Python 手动创建 lowdown.pc

### 问题6: chmod 不生效
- **现象**: `Permission denied` 运行 configure
- **原因**: HMDFS chmod 限制（E046）
- **修复**: 使用 `/system/bin/sh ./configure` 显式调用

## 编译结束
**时间**: 2026-07-13  
**最终状态**: success  
**备注**: 成功编译并通过 conan create 验证（G1-G4+L2+L4+L5 全门禁通过）
