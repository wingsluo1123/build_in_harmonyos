# libsmb2 6.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-23
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. **构建系统检测**: 项目根目录有 CMakeLists.txt 和 configure.ac（autotools），实际编译使用 CMake
2. **configure（cmake）**:
   ```
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ..
   ```
   - CMake 检测到 HarmonyOS 平台（输出 "System is unknown to cmake" 警告，但不影响编译）
   - 所有需要的头文件均找到（arpa/inet.h, fcntl.h, netdb.h, poll.h 等）
   - gssapi/gssapi.h 和 krb5/krb5.h 未找到（不影响核心功能）
   - HAVE_SOCKADDR_STORAGE=Success, HAVE_LINGER=Success, HAVE_SOCKADDR_LEN=Failed
3. **make**: 全部 49 个源文件编译成功，链接生成 libsmb2.so
   - 编译器警告：sys/errno.h 和 sys/poll.h 重定向警告（平台特性，不影响功能）
4. **make install (DESTDIR)**: 安装到 staging 目录
   - 库: libsmb2.so
   - 头文件: smb2/libsmb2.h, smb2/smb2.h 等 8 个头文件
   - pkg-config: libsmb2.pc
   - cmake config: FindSMB2.cmake, libsmb2-config-version.cmake
5. **package**: 预编译包生成成功 (libsmb2-6.2-ohos-aarch64.tar.gz: 481KB)
6. **make install (local)**: 安装到 $DEFAULT_PREFIX 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake "System is unknown to cmake" 警告 | HarmonyOS 平台未被 CMake 内置识别 | 警告不阻塞编译，CMake 仍能正确检测编译器和头文件 |
| 2 | sys/errno.h, sys/poll.h 重定向警告 | 鸿蒙 sysroot 头文件重定向到标准位置 | 警告不阻塞，功能正常 |
| 3 | make check 返回错误 | CMake 项目无 check/test 目标 | 记录为 N/A，通过 ELF 完整性和 pkg-config 验证替代 |
| 4 | G0 clean-verify 失败 | manifest.yaml 错误标记为 autotools，G0 尝试运行 ./configure | 修正 manifest.yaml 为 cmake |
| 5 | G4 报告 "manifest 缺少 build_system" | 同问题 4 | 同问题 4 修正 |
| 6 | pkg-config .pc 文件版本为 6.1.0 | 上游 CMakeLists.txt 硬编码版本号 | 不影响功能，版本号 6.2 在包名和 manifest 中正确记录 |
| 7 | 软件级 README.md 缺失 | init-build 未创建软件级目录 | 手动创建 archives/l/libsmb2/README.md |
| 8 | notes.md 为模板占位符 | finish 自动生成的模板未被填充 | 手动更新为实际编译记录 |

## 源码修改

无源码修改。libsmb2 6.2 在鸿蒙平台上无需任何补丁即可编译通过。

## 依赖版本

- 编译器: clang 15.0.4
- CMake: 3.30.0
- GNU Make: 4.4.1
- 无外部库依赖（纯 C 实现，仅依赖 libc）

## 验证结果

```bash
# pkg-config 验证
$ PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig pkg-config --modversion libsmb2
6.1.0

# ELF 文件验证
$ file /storage/Users/currentUser/usr/local/lib/libsmb2.so
ELF shared object, 64-bit LSB arm64, not stripped

# 库依赖检查
$ readelf -d /storage/Users/currentUser/usr/local/lib/libsmb2.so | grep NEEDED
NEEDED Shared library: [libc.so]

# 导出符号检查
$ nm -D /storage/Users/currentUser/usr/local/lib/libsmb2.so | grep smb2_
000000000000a4a0 T smb2_close_tree
000000000000a5f4 T smb2_connect
000000000000a8ec T smb2_disconnect
000000000000aae0 T smb2_get_error
000000000000ab0c T smb2_get_nterror
...（大量 smb2_* 符号）

# 链接+运行测试
$ clang -o test_libsmb2 test_libsmb2.c -L$DEFAULT_PREFIX/lib -lsmb2 -I$DEFAULT_PREFIX/include
$ LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib ./test_libsmb2
libsmb2 initialized successfully
libsmb2 destroyed successfully
Link + Run test: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libsmb2-6.2-ohos-aarch64.tar.gz | 481KB | 预编译包（ELF签名+RPATH+strip） |
| libsmb2-6.2-ohos-aarch64-debug.tar.gz | 86KB | 调试符号包 |

## 注意事项

- libsmb2 的 pkg-config 文件 (.pc) 中版本号为 6.1.0，这是上游 CMakeLists.txt 的硬编码问题，实际编译版本为 6.2
- 项目同时支持 autotools (configure.ac) 和 CMake (CMakeLists.txt)，本次编译使用 CMake
- 无需 Kerberos/GSSAPI 即可使用核心 SMB 功能（NTLM 认证足够）
- 库仅依赖 libc.so，无外部库依赖，适合嵌入式/鸿蒙环境

---

**编译结束**: 2026-07-23 20:41
**最终状态**: published
