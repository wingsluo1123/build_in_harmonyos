# nmap 7.95 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤
```bash
# 1. 初始化
python3 ohc-run.py init-build nmap 7.95 --url=https://nmap.org/dist/nmap-7.95.tgz --no-download

# 2. 配置（需要设置 TMPDIR）
export TMPDIR=~/.tmp
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --without-zenmap --without-ndiff --without-nmap-update

# 3. 编译（跳过 zenmap）
make nmap -j1
make -C ncat
make -C nping
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | configure: umask 077 创建临时目录权限拒绝 | E011: HMDFS 文件系统 UID 映射导致权限问题 | conanfile.py 中 _fix_umask_all() 方法替换 umask 077→022 | E011 |
| 2 | config.guess/config.sub 不识别 HarmonyOS | E007: GNU config.guess 不包含 HarmonyOS 检测 | conanfile.py 中 _fix_config_sub_all() 方法添加 linux-ohos 支持 | E007 |
| 3 | sockaddr_storage 重定义冲突 | E091/E119: OHOS 内核头文件冲突 | conanfile.py 中 _fix_sockaddr_storage() 方法添加 #define 守卫 | E091 |
| 4 | libpcre automake 试图重新生成 aclocal.m4 | automake 缺失，Makefile 依赖时间戳触发 | conanfile.py 中 _touch_source_files() 设置源文件旧时间戳 | - |

## 源码修改
所有修改在 conanfile.py build() 方法中通过 Python 代码完成，不使用 patch 文件。
原因：patches 难以应用到官方 tarball（git repo 与 SVN tarball 差异），代码方式更可靠。

## 依赖版本
- pcre2: 内嵌 libpcre2-10.43
- zlib: 内嵌 zlib-1.3.1
- lua: 内嵌 liblua-5.4.6
- libpcap: 内嵌 libpcap-1.10.4
- libdnet: 内嵌 libdnet-1.12

## 验证结果
```bash
# nmap 二进制生成成功
nmap --version
# Nmap version 7.95 ( https://nmap.org )
# Platform: aarch64-unknown-linux-ohos

# ncat 二进制生成成功
ncat --version
# Ncat: Version 7.95

# nping 二进制生成成功
nping --version
# Nping version 0.7.95
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| nmap | 3.6MB | 主扫描工具 |
| ncat | 689KB | netcat 替代工具 |
| nping | 780KB | ping 工具 |

## 注意事项
1. zenmap (Python GUI) 因缺少 Python build 模块未编译，使用 --without-zenmap 跳过
2. 所有 configure 脚本需要修复 umask 077 → 022（在 conanfile.py 中处理）
3. 所有 config.guess/config.sub 需要应用 HarmonyOS 补丁（在 conanfile.py 中处理）
4. 包含 linux/if.h 的源文件需要添加 sockaddr_storage 守卫（在 conanfile.py 中处理）

**编译结束**: 2026-08-07
**最终状态**: built
