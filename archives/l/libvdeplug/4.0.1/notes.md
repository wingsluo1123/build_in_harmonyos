# libvdeplug 4.0.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 rd235/vdeplug4，CMakeLists 顶层 project VERSION 4.0.0）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: published

## 编译步骤

1. conan download libexecs/1.4 -r=ohpcd 验证依赖可消费（配方 + OHOS armv8 静态二进制均就绪）
2. 探索性构建：cmake + make -j4 + make install DESTDIR=staging，裸环境 smoke（env -u LD_LIBRARY_PATH）
3. conan-init 生成骨架后改写 conanfile.py 为 CMake 配方（E1013 修法）
4. conan create -pr:a ci/conan/profiles/ohos-aarch64 --build=missing（含 test_package 消费者测试）
5. conan-verify（G0-G4 + L2/L4/L5 全 PASS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libvdeplug.c:55 `RTLD_DEEPBIND` 未声明 | OHOS musl libc 不提供该宏 | 补丁 0001：`#ifndef RTLD_DEEPBIND` 兜底为 0（libc 特性探测，非平台宏） |
| 2 | ld.lld 警告 cannot find entry symbol xport-dynamic | lld 将裸 `-export-dynamic` 解析为 `-e xport-dynamic`；DSO 默认导出全局符号 | 补丁 0002：注释两处 `target_link_libraries(... -export-dynamic)` |
| 3 | 共享库无 SONAME、vde_plug 的 NEEDED 记为构建树相对路径 `../libvdeplug4/libvdeplug.so`，裸环境无法加载 | 本机 CMake 4.1.2 判定 `CMAKE_SYSTEM_NAME=HarmonyOS`，无 Platform/HarmonyOS.cmake → 平台模块回落 generic，SONAME/RPATH 标志全空（知识图谱 E1013 精确命中） | conanfile.py generate() 写 ohos-cmake-rules.cmake（SONAME/RUNTIME/RPATH_LINK/ORIGIN_TOKEN 取 Platform/Linux.cmake 值）经 `CMAKE_USER_MAKE_RULES_OVERRIDE_C` 注入；`CMAKE_BUILD_WITH_INSTALL_RPATH=ON` + `CMAKE_INSTALL_RPATH=$ORIGIN;$ORIGIN/../lib` 防 install 期 RPATH 改写破坏签名 |
| 4 | 顶层 find_library(execs) FATAL + vdeplug_cmd 链接裸 `-lexecs` 找不到库 | 上游硬依赖 libexecs（coprocsp），且 CMake 只 include 项目目录 | conan requires libexecs/1.4；tc.variables 注入 `CMAKE_C_FLAGS=-I<inc>`、`CMAKE_LIBRARY_PATH`/`CMAKE_{SHARED,EXE}_LINKER_FLAGS=-L<lib>` |
| 5 | /data/storage/el2/base/cache 中途被系统回收，builds/ 整目录消失 | el2 cache 为可回收分区（项目记忆已知） | 工作目录迁移至 worktree 内 .lvdp-work/（el1 持久存储），build-context 同步改写 |

## 源码修改（经 patches/ 固化）

- 0001-libvdeplug-rtld-deepbind-musl.patch：libvdeplug4/libvdeplug.c dlopen 前补 RTLD_DEEPBIND 兜底定义
- 0002-libvdeplug4-cmake-remove-export-dynamic.patch：libvdeplug4/CMakeLists.txt 移除两处裸 -export-dynamic

## 依赖版本

- libexecs/1.4（vdeplug_cmd 插件 coprocsp()；静态链接进 libvdeplug_cmd.so，无运行时依赖）

## 验证结果

```bash
# conan create（G2）+ test_package 消费者测试 6/6 PASS，rc=0
conan create archives/l/libvdeplug/4.0.1 -pr:a ci/conan/profiles/ohos-aarch64 --build=missing
# 包产物 ELF 元数据
llvm-readelf -d <pkg>/lib/libvdeplug.so
#   (SONAME)  Library soname: [libvdeplug.so.2]
#   (RUNPATH) Library runpath: [$ORIGIN:$ORIGIN/../lib]
# 裸环境 smoke（无 LD_LIBRARY_PATH）
env -u LD_LIBRARY_PATH <pkg>/bin/vde_plug null:// </dev/null   # rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libvdeplug.so(.2/.4.0.0) + libvdeplug.a | 主库（SONAME libvdeplug.so.2） |
| lib/libvdeplug_mod.so(.2/.4.0.0) | 插件基础设施库 |
| lib/vdeplug/libvdeplug_*.so（13 个） | vde/ptp/tap/udp/vxlan/vxvde/cmd/null/hub/switch/multi/bonding/seqpacket 插件 |
| bin/vde_plug, bin/dpipe | 命令行工具（软件级 commands.json 已声明） |
| include/libvdeplug.h, libvdeplug_mod.h | 头文件 |

## 上游测试

上游无自动化测试（清点证据见 test_package/MANIFEST.yml）：无 tests/ 目录、5 个 CMakeLists.txt 无
add_test()/enable_testing()、无 make check 目标。test_package 提供 7 断言消费者测试（鸿蒙用例）补位。

## 注意事项

- 分支 feat/libvdeplug-4.0.1；worktree archives/l/libXext 的 README/manifest 暂存改动为 HMDFS 大小写不敏感伪影，勿提交
- /data/storage/el2/base/cache 会被系统回收，本包工作目录固定在 worktree 内 .lvdp-work/
- 探索期 refresh-patch --auto 曾因 HMDFS 抖动产出 5 个全文件误判补丁，已弃用并手工生成规范补丁（manifest 中 patch_generation 段已清理）
---

**编译结束**: 2026-10-17 20:55
**最终状态**: published
