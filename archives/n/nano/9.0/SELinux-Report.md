# HMDFS SELinux 限制技术报告

## 问题摘要

**日期**: 2026-05-27
**影响软件**: nano 9.0 源码编译（以及其他 autotools 项目）
**阻塞阶段**: configure/config.status 执行
**根本原因**: HMDFS 文件系统 SELinux 强制访问控制限制

## 详细描述

### 现象
在编译 nano 9.0 及其依赖 ncurses 6.4 时，configure/config.status 脚本执行失败：

```
tail: cannot fstat 'standard input': Permission denied
head: 'standard input': cannot seek to relative offset: Permission denied
config.status: cannot create temporary file: Permission denied
```

### 根因分析

1. **HMDFS SELinux MAC 限制**
   - HMDFS（HarmonyOS 分布式文件系统）实施 SELinux 强制访问控制
   - 普通用户进程无法读取特定类型的临时文件，即使文件权限位允许
   - shell 命令（cat/grep/sed/head/tail）被 SELinux 拒绝访问

2. **临时目录权限继承**
   - `mktemp -d` 创建的目录权限为 `drwxrws--x`（2771，带 setgid）
   - `umask 077` 设置不生效
   - 目录继承组权限而非用户权限

3. **影响范围**
   - 所有使用 autotools 构建系统的项目
   - 需要 config.status 创建/读取临时文件的 configure 流程

### 技术验证

```bash
# 测试 HMDFS 临时文件读取
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
tmpfile=$(mktemp $TMPDIR/testXXXXXX)
echo "test content" > $tmpfile
cat $tmpfile  # Permission denied
python3 -c "open('$tmpfile').read()"  # 成功（Python 可读）

# 测试目录权限
umask 077
tmpdir=$(mktemp -d $TMPDIR/dirXXXXXX)
ls -ld $tmpdir  # drwxrws--x (2771) 而非 drwx------ (700)
```

## 需要的解决方案

### 方案 A：SELinux Policy 调整（推荐）

调整 SELinux policy，允许编译工具链（clang/gcc/make/sh）访问 HMDFS 临时文件：

```bash
# 示例命令（需要管理员权限）
# 1. 查看当前 SELinux 模式
getenforce

# 2. 临时调整为 Permissive（测试用）
setenforce 0

# 3. 或添加 policy 规则
# semanage fcontext -a -t tmp_t "$HOME/tmp(/.*)?"
# restorecon -R $HOME/tmp
```

### 方案 B：提供非 HMDFS 临时目录

在系统上提供一个不受 SELinux HMDFS 限制的临时目录路径：

```bash
# 建议路径（需要管理员创建并配置权限）
mkdir -p /data/local/tmp
chmod 1777 /data/local/tmp
# 调整 SELinux 类型标签
chcon -t tmp_t /data/local/tmp
```

### 方案 C：配置 autotools wrapper

为 autotools 项目创建 wrapper，在 config.status 执行前设置 TMPDIR：

```bash
# wrapper 脚本示例
export TMPDIR=/data/local/tmp  # 或其他可写路径
exec ./configure "$@"
```

## 已验证的可替代方案

- **nano 7.2 预编译包**: 已安装可用（`~/usr/local/bin/nano --version`）
- **ncurses 库**: libncursesw.a 和头文件已通过 Python 工具生成

## 相关知识图谱条目

- **E002**: HMDFS /tmp 只读问题
- **E046**: chmod 不生效（SELinux 限制）
- **E081**: HMDFS mktemp 临时目录权限继承问题（新发现）

## 联系信息

如有问题或需要进一步技术细节，请联系编译适配团队。

---

**附件**:
- config.log 文件位置: `~/tmp/builds/nano-9.0.work/config.log`
- ncurses config.log: `~/tmp/builds/ncurses-6.4.work/config.log`（如存在）