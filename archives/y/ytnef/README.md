# ytnef — TNEF Stream Reader

## 简介

ytnef 是一个用于解析 Microsoft TNEF (Transport Neutral Encapsulation Format) 流文件的工具库。
TNEF 格式通常用于 winmail.dat 附件，常见于 Microsoft Exchange/Outlook 邮件系统。

## 组件

| 组件 | 类型 | 说明 |
|------|------|------|
| libytnef | C 库 | TNEF 解析核心库，提供静态库 (.a) 和共享库 (.so) |
| ytnef | 可执行文件 | TNEF 导出器，解析 winmail.dat 并提取附件 |
| ytnefprint | 可执行文件 | TNEF 打印器，输出 TNEF 流内容 |
| ytnefprocess | Perl 脚本 | TNEF 处理器（需要 Perl 解释器） |

## 依赖

- **无外部依赖** — libytnef 库包含在源码 lib/ 子目录中
- ytnefprocess 需要 `/usr/bin/perl`（在无 Perl 的平台上不可用）

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 2.1.2 | built | autotools |

## 构建说明

```bash
# 1. 下载源码
curl -kL -o ytnef-2.1.2.tar.gz "https://api.github.com/repos/Yeraze/ytnef/tarball/v2.1.2"

# 2. 解压并进入目录
tar xzf ytnef-2.1.2.tar.gz
cd Yeraze-ytnef-*

# 3. 生成 configure 脚本（tarball 不含预生成文件）
autoreconf -vfi

# 4. 修复 HMDFS 权限问题 (E011)
sed -i 's/umask 077/umask 022/g' configure

# 5. 配置、编译、安装
./configure --prefix=$PREFIX
make -j1
make install
```

## 许可证

GPL (详见源码 COPYING 文件)
