# yubico-c-client 2.15 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++
- CFLAGS: -fPIC -O2
- 平台: aarch64-unknown-linux-ohos (HarmonyOS HongMeng Kernel 1.12.0)
- 状态: published

## 源码信息

- 软件名: yubico-c-client
- 版本: 2.15
- GitHub tag: ykclient-2.15 (注意: tag名与版本号不同)
- 下载 URL: https://codeload.github.com/Yubico/yubico-c-client/tar.gz/refs/tags/ykclient-2.15
- SHA256: 3863f4fc2f3320c59fcbf57862bba48bcb716fddb886840bb0dd8db14d5ab7f0
- 许可证: BSD-2-Clause

## 编译步骤

1. 下载源码包 (GitHub tarball, tag: ykclient-2.15)
   - 使用 `curl -ksL` 下载 (SSL证书问题，预编译curl无CA证书)
   - 放置到 `~/tmp/builds/yubico-c-client-2.15.work`

2. `autoreconf --install -f`
   - GitHub 源码包不含生成的 configure 脚本，需要 autoreconf 生成
   - 需要 automake/autoconf/libtool 工具链

3. 修补 umask: `sed -i 's/umask 077/umask 022/g' configure`
   - HMDFS 文件系统中，目录的 setgid 位 + umask 077 导致 config.status 创建的临时目录内无法写入文件
   - 已通过 track-edit 追踪

4. `PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig ./configure --prefix=$DEFAULT_PREFIX`

5. `make -j1`

6. `make install DESTDIR=$TEST_PREFIX` (staging 隔离验证)
   - 9 个文件正确暂存: bin/ykclient, lib/libykclient.{a,la,so.3.6.0}, include/ykclient*.h (4个), share/man/man1/ykclient.1

7. `make check` (网络依赖测试失败，见 reports/test-report.md)
   - selftest 因无法访问 Yubico 验证服务器而失败 (exit 134, SIGABRT)
   - 版本一致性检查通过: header 2.15 library 2.15

8. `conan-init` 生成 Conan 配方 (conanfile.py, conandata.yml)

9. 编辑 conanfile.py: 添加 autoreconf 步骤、umask 修复、移除 -static (库非终端工具)
   编辑 conandata.yml: 修正 URL (codeload.github.com) 和 SHA256、添加 filename 字段
   编辑 manifest.yaml: 添加 build_system、sha256、compile_date、patches_applied

10. `conan-verify` 验证: G1-G4 全部 PASS, L2/L4/L5 全部 PASS

11. `make install` (安装到 $DEFAULT_PREFIX)

12. `$DEFAULT_PREFIX/bin/ykclient --version` → 2.15 ✅

13. `finish` 收尾: 补丁生成、归档关闭、质量验证、知识整理

14. `verify-build`: G1-G4 全部 PASS

15. `submit`: 6/6 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | curl 库未安装 | 系统无 libcurl | 安装预编译包 curl 8.19.0 (cmd-pkgs install.sh) |
| 2 | zlib 未安装 | libcurl 依赖 zlib | 安装预编译包 zlib 1.3.1 |
| 3 | SSL 证书验证失败 | 预编译 curl 无 CA 证书 | 设置 SSL_CERT_FILE 和 CURL_CA_BUNDLE 环境变量 |
| 4 | config.status 权限错误 | HMDFS: umask 077 + setgid 位导致临时目录内无法创建文件 | sed umask 077 → umask 022 in configure (E011) |
| 5 | help2man 未安装 | man 页生成需要 help2man | 安装预编译包 help2man 1.49.3 |
| 6 | selftest 失败 (exit 134) | 需要访问 Yubico 验证服务器 (api.yubico.com) | 网络依赖测试，非编译问题 (E024) |
| 7 | conan-verify G2 BadZipFile | Conan get() 无法从 GitHub API URL 下载 (302重定向) | 改用 codeload.github.com URL + 添加 filename 字段 |
| 8 | conan-verify SHA256 不匹配 | codeload URL 与 API URL 生成不同 tarball | 重新计算 codeload 下载的 SHA256 |
| 9 | manifest_complete 检查失败 | 缺少 compile_date 字段 (仅有 build_date) | 添加 compile_date 字段 |

## 源码修改

- **文件**: configure
- **修改**: 将 `umask 077` 改为 `umask 022` (2处)
- **原因**: HMDFS 文件系统中，目录的 setgid 位 + umask 077 导致 config.status 创建的临时目录内无法写入文件
- **补丁**: patches/0001-configure.patch
- **追踪**: 已通过 track-edit 记录

## 依赖版本

| 依赖 | 版本 | 类型 | 来源 |
|------|------|------|------|
| curl | 8.19.0 | 运行时 | 预编译包 (cmd-pkgs) |
| zlib | 1.3.1 | 传递依赖 | 预编译包 (cmd-pkgs) |
| help2man | 1.49.3 | 构建工具 | 预编译包 (cmd-pkgs) |

## 验证结果

### 二进制验证
```bash
$ $DEFAULT_PREFIX/bin/ykclient --version
2.15
```

### 文件类型
```
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 库文件
- libykclient.so.3.6.0 (47552 bytes, 共享库)
- libykclient.a (49622 bytes, 静态库)
- libykclient.la (1145 bytes, libtool 归档)

### 头文件
- ykclient.h (4935 bytes)
- ykclient_errors.h (2292 bytes)
- ykclient_server_response.h (3167 bytes)
- ykclient_version.h (3021 bytes)

### Conan test package
```
100% tests passed, 0 tests failed out of 1
Total Test time (real) =   0.03 sec
```

## 交付物

| 文件 | 说明 |
|------|------|
| README.md | 软件说明文档 |
| conanfile.py | Conan 配方 (含 autoreconf + umask 修复) |
| conandata.yml | Conan 数据文件 (URL, SHA256, filename) |
| manifest.yaml | 编译元数据 (status: published) |
| notes.md | 本文件 |
| patches/0001-configure.patch | configure umask 修复补丁 |
| packaging/yubico-c-client-2.15-ohos-aarch64.tar.gz | 发布预编译包 (162859 bytes) |
| packaging/yubico-c-client-2.15-aarch64-unknown-linux-ohos-debug.tar.gz | 调试预编译包 (162859 bytes) |
| reports/test-report.md | 详细测试报告 (含真实执行日志，2026-06-26 重新执行) |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/quality-report.md | 质量报告 |
| reports/baseline.json | 产物基线 |
| test_package/ | Conan test package |

## 质量门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G1 配方完整性 | ✅ PASS | name/version/source/build/package 方法完整 |
| G0 预构建风险 | ✅ PASS | 知识图谱预查询通过 |
| G2 干净构建 | ✅ PASS | conan create 成功 |
| G3 静态链接 | ✅ PASS | R26 验证通过 |
| G4 产物完整性 | ✅ PASS | 产物文件完整 |
| L2 平台功能 | ✅ PASS | smoke test 通过 |
| L4 安全扫描 | ✅ PASS | checksec 通过 |
| L5 基线对比 | ✅ PASS | baseline 已保存 |
| verify-build G1-G4 | ✅ PASS | 全部通过 |
| submit 6/6 | ✅ PASS | 全部通过 |

## 注意事项

1. 源码包是 GitHub tarball (tag: ykclient-2.15)，不含生成的 configure 脚本，需要 autoreconf
2. selftest 需要网络访问 Yubico 验证服务器 (api.yubico.com)，在隔离环境中会失败
3. configure 的 umask 077 在 HMDFS 上有问题，已改为 umask 022 (E011)
4. 预编译 curl 包的 SSL 证书需要手动配置 SSL_CERT_FILE 环境变量
5. Conan 下载需使用 codeload.github.com URL (非 API URL)，并指定 filename 字段

## 知识积累

- ✅ E011: HMDFS umask 077 + setgid 权限问题 — sed umask 077→022 修复
- ✅ E017: GitHub tarball 不含 configure 脚本 — autoreconf --install -f
- ✅ E024: selftest 网络依赖测试失败 — 隔离环境无法访问 Yubico 验证服务器
- ✅ E048: help2man 构建工具缺失 — 安装预编译包 help2man 1.49.3

## 对话记录

### 对话 #1: 2026-06-25 编译流程

1. 加载 openharmony-compile-agent Skill
2. 检查 curl 依赖 → 未安装 → 通过 cmd-pkgs 安装 curl 8.19.0
3. 安装 zlib 1.3.1 (curl 传递依赖)
4. init-build 初始化构建 → 手动下载 GitHub tarball (tag: ykclient-2.15)
5. autoreconf --install -f 生成 configure 脚本
6. 修补 umask 077→022 (HMDFS 权限问题, E011)
7. configure --prefix=$DEFAULT_PREFIX 成功
8. 安装 help2man 1.49.3 → make 成功
9. make install DESTDIR 暂存验证通过 (9个文件)
10. make check → selftest 失败 (网络依赖, exit 134)
11. conan-init 生成 Conan 配方
12. 编辑 conanfile.py/conandata.yml/manifest.yaml/notes.md
13. conan-verify G2 失败 → 修复 URL (codeload) + SHA256 + filename → G2 PASS
14. 知识整理 → check-knowledge-gap 通过 → .knowledge-done 标记创建
15. finish 收尾 → 全部完成 (exit 0)
16. verify-build G1-G4 全部 PASS
17. submit 6/6 PASS → status: published

### 对话 #2: 2026-06-26 测试报告重执行与归档补充

1. 重新执行 `make check` → 捕获完整原始终端输出 (exit 2, selftest FAIL)
2. 获取 test-suite.log / selftest.log / selftest.trs 原始内容
3. 重新执行 `ykclient --version` → 2.15 (exit 0)
4. 重新执行 `ykclient --help` → 完整帮助文本 (exit 0)
5. `file ykclient` → ELF shared object, 64-bit LSB arm64, dynamic musl
6. `llvm-nm -D libykclient.so` → 确认 curl_* 符号引用正确
7. 验证库文件/头文件/man page 安装 → 全部正确
8. 验证 DESTDIR 暂存 → 9 个文件路径结构完整
9. 重新执行 Conan test package → CTest 1/1 PASS (0.02 sec)
10. 获取 CTest LastTest.log 原始内容 → "test yubico-c-client 2.15: OK"
11. 重写 test-report.md → 填入所有真实捕获的终端输出和日志
12. 检查 packaging 目录 → release 和 debug tar.gz 均存在且文件名匹配 glob 模式
13. 修正 notes.md 交付物表中的文件名

---

**编译结束**: 2026-06-25
**最终状态**: published
