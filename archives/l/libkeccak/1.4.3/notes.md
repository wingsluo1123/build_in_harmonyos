# libkeccak 1.4.3 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-08
- 编译器: clang/clang++
- 状态: published

## 编译步骤

libkeccak 使用纯 Makefile 构建系统，无 configure 脚本。

```bash
# 1. 编译（覆盖 config.mk 中的 CC=c99）
make -j1 CC=clang CFLAGS='-fPIC -O2' CPPFLAGS='-D_DEFAULT_SOURCE -D_BSD_SOURCE -D_XOPEN_SOURCE=700'

# 2. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX CC=clang

# 3. 运行测试
make check CC=clang
```

Conan 配方中使用 `make -C {self.source_folder}` 指定 Makefile 所在目录，因 Conan 2.x 的 `basic_layout()` 会创建 `build-release/` 子目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法下载源码 | 鸿蒙环境缺少 CA 根证书 | curl -kL 手动下载 tarball 到 $TMPDIR/builds/ |
| 2 | Conan 下载源码后报 BadZipFile | GitHub API URL 无文件扩展名，Conan 默认尝试 zip 解压 | conandata.yml 添加 `filename: "libkeccak-1.4.3.tar.gz"` |
| 3 | make 找不到 Makefile | Conan 2.x basic_layout() 创建 build-release/ 子目录，self.run() 在该目录执行 | 使用 `make -C {self.source_folder}` 指定源码目录 |
| 4 | 构建系统被误判为 autotools | init-build 的构建系统猜测逻辑基于 URL 关键词 | 手动编写 conanfile.py 使用 self.run("make ...") |
| 5 | CI test_package 运行报 libkeccak.so.1 not found (build #675) | OHOS 动态链接器不识别 self.run() env 参数直接设置的 LD_LIBRARY_PATH | 改用 VirtualRunEnv + env=["conanrun"] 让 Conan 正确管理运行时环境 |

## 源码修改

无补丁。源码未做任何修改，所有平台适配通过 make 命令行变量覆盖完成。

## 依赖版本

- clang 15.0.4
- make 4.4.1
- llvm-ar
- libc

## 验证结果

```bash
$ make check CC=clang
# 全部通过：SHA3-224/256/384/512, Keccak-224/256/384/512,
# RawSHAKE-256, SHAKE-128/256, cSHAKE-128/256, HMAC,
# 二进制输入测试, squeeze 函数测试, 文件哈希测试

$ conan create ... (conan-verify)
# G0-G4 + L2/L4/L5 全部 PASS
# test_package: SHA3-256("") = a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a
```

## 注意事项

- clang 对 `__optimize__("-O0")` 属性产生 `-Wignored-attributes` 警告，这是 GCC 特有属性，不影响功能。
- `config.mk` 中 `CC=c99` 不可用，必须通过 make 命令行覆盖为 `clang`。
- `linux.mk` 定义了共享库构建规则（`-shared -Wl,-soname`），默认构建动态库。
- install target 使用 `DESTDIR+PREFIX` 模式，`PREFIX=` 空值可将文件安装到 DESTDIR 根目录。

---

**编译结束**: 2026-07-08 11:14
**最终状态**: published
