# libtcd 2.2.7 — 适配笔记

## 基本信息

- **软件**: libtcd (Tide Constituent Data format library)
- **版本**: 2.2.7 (upstream revision r3)
- **构建系统**: autotools (configure + make)
- **源码**: https://flaterco.com/files/xtide/libtcd-2.2.7-r3.tar.xz
- **SHA256**: e1dde9aafb771eab57c676a99b4b79d61c6800990a0e72782bc20057a8a2d877
- **许可证**: Public Domain
- **依赖**: 无第三方依赖（仅链接 libm）

## 首个错误与根因分析

### 错误1: config.guess 不识别 HarmonyOS
- **现象**: `configure` 报 `config.guess: unable to guess system type`
- **根因**: 源码自带的 config.guess 时间戳为 2014-11-04，不识别 HarmonyOS 平台
- **修复**: conanfile.py 内联 replace_in_file 补丁，添加 HarmonyOS 检测到 config.guess 和 config.sub
- **知识条目**: E005

### 错误2: config.status 创建临时文件 Permission denied
- **现象**: `config.status[970]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS UID 映射机制下，`umask 077` 创建的 0700 权限目录进程无法写入
- **修复**: `sed -i 's/umask 077/umask 022/g' configure`
- **知识条目**: E011

## 编译过程

```bash
source .build-context-libtcd-2.2.7
cd $BUILD_SRC_DIR
# 替换 config.guess/config.sub
# 修复 umask
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

编译成功，有 6 个 format 警告（benign，format string 类型不匹配）。

## 上游测试 (R51)

### 清点
- Makefile.am 中无 `check_PROGRAMS`、`TESTS` 或 test target
- 无 `tests/` 目录
- `make check` 输出 "Nothing to be done for 'check'"

### 结果
| 项目 | 数量 |
|------|------|
| 总计 | 0 |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |

**上游无测试套件。** Conan test_package 提供 API 级冒烟测试（ret_date/ret_time）。

## 产物

- `lib/libtcd.so.1.0.2` (shared, with symlinks libtcd.so.1, libtcd.so)
- `lib/libtcd.a` (static)
- `include/tcd.h`
- `share/libtcd/libtcd.html`
---

**编译结束**: 2026-10-16 20:58
**最终状态**: built
