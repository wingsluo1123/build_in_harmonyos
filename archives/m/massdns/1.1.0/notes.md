# massdns 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
make clean
make CC=clang -j1
# 手动安装（Makefile install target uses `install` command not available on OHOS）
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/share/man/man1
cp bin/massdns $TEST_PREFIX$DEFAULT_PREFIX/bin/
chmod 0755 $TEST_PREFIX$DEFAULT_PREFIX/bin/massdns
cp doc/massdns.1 $TEST_PREFIX$DEFAULT_PREFIX/share/man/man1/
chmod 0644 $TEST_PREFIX$DEFAULT_PREFIX/share/man/man1/massdns.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | git describe 失败 | 非 git 仓库 | MASSDNS_REVISION 为空，不影响功能 |
| 2 | make -j2 fifo 权限 | HMDFS 不支持 mkfifo | 使用 -j1 (R9) |
| 3 | install 命令不存在 | 鸿蒙无 GNU coreutils install | 手动 cp + chmod |
| 4 | 测试脚本用 #!/bin/bash | 鸿蒙 bash 不在 /bin | 跳过集成测试，二进制验证通过 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1

## 验证结果

```bash
$ ./bin/massdns --version
massdns

$ ./bin/massdns --help
Usage: ./bin/massdns [options] [domainlist]
  -b  --bindto           Bind to IP and port. (Default: 0.0.0.0:0)
  ...
```

编译警告（不影响功能）：
- src/main.c:987: warning: incompatible pointer types (sockaddr_in6 vs sockaddr)
- src/main.c:1616: warning: variable 'rec_index' set but not used

## 二次校准 (2026-07-17)

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 5 | R33: build() 依赖裸 $(CC) | Makefile 用 $(CC) 但未从 Conan profile 传入 | 添加 _compiler_c() + generate() + 显式传 CC |
| 6 | R32: 缺少 validate() | 未检查平台兼容性 | 添加 validate() 检查 Linux/OHOS |
| 7 | test.sh set -eu 命令替换缺陷 | `OUTPUT=$(cmd)` 失败时 set -e 直接退出 | 改用 `|| true` + grep 检查 |
| 8 | README 无效 Savannah 链接 | massdns 不在 Savannah | 移除无效链接 |

## 注意事项

1. massdns 是高性能 DNS stub resolver，用于批量域名解析
2. 无 configure 脚本，直接 make 编译
3. 使用 `-DHAVE_EPOLL -DHAVE_SYSINFO` Linux 特定选项
4. 命令行工具 (application)，非库
5. conanfile.py 中 package_type = "application"，需要 commands.json (R38)
6. test_package 运行 `massdns --version` 验证二进制可用 (R34)
---

**编译结束**: 2026-07-15 22:51
**最终状态**: built
