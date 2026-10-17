# libproxyprotocol 1.3.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. `git worktree add -b feat/libproxyprotocol-1.3.3 <wt> main` 从 main (c611f7d6) 创建唯一专用 worktree
2. `ohc-run.py init-build libproxyprotocol 1.3.3 --url=<官方 tag 归档 URL>`
   - 官方源核验: tag v1.3.3, commit 3e133b9602e59f47ceceef74fbd52a3b147e5874 (经 GitHub API 确认)
   - SHA-256: 4f1cbd714e5b52a91a9a43228d55c8165b578b738f743d057ae321b69b8437f7
   - 注: github.com 主站超时，通过官方 codeload CDN 下载同一归档
3. `ohc-run.py lang-preflight`: task=cpp, detected=c → 兼容族通过
4. 源码评估: ANSI C 库，仅 #ifdef _WIN32 平台分支，无 OHOS 特定代码，无需源码补丁
5. `make CC=clang all` 编译: libs/libproxyprotocol.so + 上游测试 + example，全部成功
6. `make tests`: 上游 124 个用例全部 PASSED（All tests completed successfully）
7. `ohc-run.py conan-init` 生成配方后手工改造为 raw-Makefile 配方（原模板为 autotools）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时 (Errno 110) | 本机到 github.com 主站网络超时 | 改用官方 codeload CDN (codeload.github.com) 下载同一 tag 归档；sha256 与官方一致 |
| 2 | init-build 反复重新下载 | TMPDIR=/storage/Users/currentUser 时 tarball 期望路径为 $TMPDIR/builds/ | 将下载的归档放入 $TMPDIR/builds/libproxyprotocol-1.3.3.tar.gz 后跳过下载 |
| 3 | conan-init 生成 autotools 模板 | 模板按 URL 猜测构建系统为 autotools | 手工重写为 raw-Makefile 配方（GnuToolchain + make CC 编译 + 手动 copy 产物） |

## 源码修改

无（纯 ANSI C 库，clang 直接编译通过，无补丁）

## 依赖版本

无第三方依赖（requirements() 为空）

## 验证结果

```bash
$ make CC=clang all
# libs/libproxyprotocol.so 编译成功
# tests/test_libproxyprotocol: 124 用例全部 PASSED
# example: client_server 运行输出 45/535 bytes PROXY header
All tests completed successfully
```

## 交付物

- libs/libproxyprotocol.so（共享库）
- include/proxy_protocol.h（公共头文件）
- conanfile.py / conandata.yml / test_package/（配方）

## 注意事项

- 上游 Makefile 无 install 目标，package() 手工 copy .so 与头文件
- 库名 libproxyprotocol.so → cpp_info.libs = ["proxyprotocol"]
- 系统无同名库（/lib /lib64 无 libproxyprotocol），非系统同名库，默认共享库形态
---

**编译结束**: 2026-09-27 17:23
**最终状态**: built
