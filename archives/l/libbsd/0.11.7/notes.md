# libbsd 0.11.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://libbsd.freedesktop.org/releases/libbsd-0.11.7.tar.xz
2. 应用补丁:
   - 0001: umask 077 → 022 (HMDFS权限问题)
   - 0002: config.guess 添加 HarmonyOS 检测
   - 0003: config.sub 添加 ohos 白名单
3. 构建 libmd 依赖 (系统无 libmd, 需从源码编译)
4. configure: `./configure --prefix=$DEFAULT_PREFIX --disable-dependency-tracking`
5. make: `make -j2`
6. install: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 Permission denied | HMDFS umask 077 创建临时目录不可写 | sed umask 077 → 022 |
| 2 | config.guess 不识别 HarmonyOS | 缺少 HarmonyOS 平台检测 | 添加 aarch64:HarmonyOS 分支 |
| 3 | config.sub 不接受 ohos 三元组 | OS 白名单缺少 ohos | 添加 ohos-linux 和 ohos* |
| 4 | 缺少 MD5/SHA-2 函数 | 系统无 libmd, libc 无 MD5Update | 从源码编译 libmd 1.1.0 |
| 5 | conan test_package 链接失败 | libbsd.so 为 libtool 脚本指向 //lib/ | package() 中删除 *.la/*.so |
| 6 | closefrom 测试失败 (Signal 31) | close_range syscall 未实现 | 平台限制, 不阻塞 |
| 7 | funopen 测试失败 | fopencookie fclose 断言失败 | 平台限制, 不阻塞 |

## 源码修改

- configure: umask 077 → 022
- build-aux/config.guess: 添加 aarch64:HarmonyOS 检测
- build-aux/config.sub: 添加 ohos-linux 映射和 ohos* 白名单

## 依赖版本

- libmd/1.1.0 (从源码编译, 已创建 conan 配方)

## 验证结果

```
conan create archives/l/libbsd/0.11.7/conanfile.py -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
→ test_package: strlcpy result: hello libbsd
→ test_package: strtonum result: 42
→ PASSED
```

上游 make check: 22/24 通过 (closefrom/funopen 平台限制)

## 注意事项

- libmd 是必需依赖, 系统无 libmd, 需创建 conan 配方
- closefrom/funopen 测试失败为 HarmonyOS 平台限制 (syscall 未实现)
- libbsd.so 为 libtool 链接器脚本, 静态构建时需删除
---

**编译结束**: 2026-08-10
**最终状态**: built
