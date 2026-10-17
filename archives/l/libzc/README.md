# libzc

## 简介
libzc 是一个简单的 zip 密码破解库（GPL-3.0），附带的命令行工具 `yazc`（Yet
Another Zip Cracker）支持暴力破解、字典攻击与明文攻击。

## 版本
- 0.4.3（上游 tag v0.4.3，2020-11-30）

## OHOS 适配
- autotools 构建；上游 tarball 无预生成 `configure`，build() 内先
  `autoreconf --install`（HNP 环境需注入 PERL5LIB/ACLOCAL_PATH，见
  conanfile.py `_prepare_autotools_env`）。
- 生成的 configure 剥离 `umask 077`（E114：HMDFS 下 0700 临时目录不可写）。
- OHOS musl 无 POSIX 线程取消 API（E127/E513）：补丁 0001 在
  `lib/zc_crk_bforce.c` 增加信号触发、保持 join 语义的回退垫片。
- zlib 依赖使用 -fPIC 重建的 zlib/1.3.1.1（上游 1.3.1 的 libz.a 非 PIC，
  无法链接进共享库 libzc.so）。

## 依赖
- zlib/1.3.1.1（必须）

## 功能验证
- 上游测试 8/8 通过（check 框架：basic/file/pwstream/bruteforce/
  dictionary/reduce/plaintext_password/plaintext，本地 `make check` 实测）。
- test_package 含 2 个测试：test_libzc（真实 API 冒烟）+ harmonyos_ohos_test
  （驱动 zc_crk_bforce，覆盖 OHOS 取消回退路径）。
