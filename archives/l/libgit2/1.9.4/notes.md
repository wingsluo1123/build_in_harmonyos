# libgit2 1.9.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境
2. cmake 配置: cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTS=ON
3. 编译: cmake --build build -j2
4. 安装: cmake --install build --prefix $DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
5. 打包: ohc-run.py package libgit2 1.9.4

## 遇到的问题与解决方案

无需修改源码，使用默认配置即可编译成功。

## 源码修改

无

## 依赖版本

- openssl: 1.1.1w
- zlib: 1.3.1
- cmake: 4.1.2

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/git2 --help
usage: git2 [--help] [-c <key=value>] [--config-env=<key=value>] [--no-pager]
             [--version] <command> [<args>...]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgit2-1.9.4-ohos-aarch64.tar.gz | 8.6MB | 主包 |
| libgit2-1.9.4-ohos-aarch64-debug.tar.gz | 6.6MB | 调试包 |

---

**编译结束**: 2026-05-27 18:25
**最终状态**: built