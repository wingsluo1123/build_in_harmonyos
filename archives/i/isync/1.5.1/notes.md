# isync 1.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: SourceForge isync-1.5.1.tar.gz
2. 更新 config.guess/config.sub（使用 automake-1.16 版本）
3. 配置: `./configure --prefix=$DEFAULT_PREFIX --with-ssl=$HOME/usr/local --with-zlib=$HOME/usr/local`
4. 编译: `make -j1`
5. 测试: `make check` (PASS: 3)
6. 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | OpenHarmony 未被识别 | 使用 automake-1.16 的最新 config.guess |
| 2 | getpass 函数不可用 | musl libc 未实现 getpass | 添加 getpass 替代实现（使用 termios） |

## 源码修改

### src/drv_imap.c
添加了 getpass() 函数的替代实现，用于 OpenHarmony 系统：
- 使用 termios 禁用终端回显
- 从 /dev/tty 或 stdin/fdout 读取密码
- 返回静态缓冲区中的密码字符串

## 依赖版本

- openssl/1.1.1 (已安装)
- zlib/1.3 (已安装)

## 验证结果

```bash
$ mbsync --version
isync 1.5.1

$ file mbsync
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mbsync | 289KB | IMAP 邮箱同步工具 |
| mbsync-get-cert | 1.5KB | 获取 SSL 证书脚本 |

## 注意事项

- OpenHarmony 使用 musl libc，缺少部分 POSIX 函数
- 密码输入功能已适配，但建议使用 PassCmd 配置选项

## Conan 适配 (2026-08-06)

### 新增修复
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 3 | config.status 无法创建临时文件 | E129: HMDFS setgid 导致 umask 077 创建 drwx--S--- 目录 | conanfile.py build() 中 sed 替换 umask 077→022 |

### Conan 配方要点
- package_type: application (非 library，产物为可执行文件 mbsync/mbsync-get-cert)
- 依赖: openssl/1.1.1w, zlib/1.3.1 (Conan 制品仓版本)
- generate(): 使用 self.dependencies 获取依赖路径，传递 --with-ssl/--with-zlib
- build(): apply_conandata_patches + umask fix (E129) + autotools configure + make -j1
- package_info(): bindirs=["bin"], 无 libs (应用程序无库文件)
- test_package: 运行 mbsync --version 验证二进制可用 (R34)
- commands.json: 已创建 (R38)
---

**编译结束**: 2026-08-06 20:40
**最终状态**: built
