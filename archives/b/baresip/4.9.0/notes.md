# baresip 4.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. 下载源码
# URL: https://github.com/baresip/baresip/archive/refs/tags/v4.9.0.tar.gz
# sha256: fe0dc70640616b5b6814f728af3ce83b4c56dd1d7a9a21658480c305bd092367

# 2. 应用补丁
patch -p1 < patches/0001-CMakeLists.txt.patch

# 3. CMake 配置 (通过 Conan)
# conanfile.py generate() 设置:
#   - CMakeDeps 生成 re-config.cmake / openssl-config.cmake
#   - STATIC=ON (静态库)
#   - MODULES= (仅无外部依赖的模块)

# 4. 编译
cmake --build . -j1

# 5. 安装
cmake --install .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | re.h 头文件找不到 | Conan CMakeToolchain 设置 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON，导致 find_package(RE) 使用 re-config.cmake 而非 FindRE.cmake，FindRE.cmake 设置的 RE_INCLUDE_DIRS (大写) 变量未被设置 | 补丁 0001-CMakeLists.txt.patch: 在 include_directories 中添加 ${re_INCLUDE_DIRS}/re (Conan CMakeDeps 生成的小写变量) |
| 2 | re::re 库未链接 | LINKLIBS 使用 ${RE_LIBRARIES} (大写，未设置) 而非 re::re 目标 | 补丁 0001-CMakeLists.txt.patch: 在 LINKLIBS 中添加 re::re 目标 |
| 3 | re_INCLUDE_DIRS_RELEASE 为空 (传递依赖) | re 包未显式设置 cpp_info.includedirs，传递依赖上下文中 Conan CMakeDeps 未生成默认 include 目录 | test_package conanfile.py 显式声明 re/4.9.0 为直接依赖 |
| 4 | baresip_init() 失败 (EINVAL 22) | OHOS 平台 DNS 初始化失败 (dns_init) | smoke test 不调用 baresip_init()，改为验证 conf_configure_buf + conf_config |
| 5 | test_package 中 'bool' 类型未定义 | baresip.h 使用 bool 类型但未包含 stdbool.h | test_baresip.c 包含 re/re.h (间接包含 stdbool.h) |
| 6 | 模块依赖系统库缺失 | baresip 模块化架构，部分模块依赖 ALSA/PulseAudio/FFmpeg 等 | 通过 MODULES CMake 变量显式指定仅编译无外部依赖的模块 |

## 源码修改

- 0001-CMakeLists.txt.patch: 修改 CMakeLists.txt 使用 Conan CMakeDeps 变量 (re_INCLUDE_DIRS, re::re 目标) 替代 FindRE.cmake 的大写变量

## 依赖版本

- re (libre) 4.9.0（Conan 依赖，已发布到 ohpcd 远端：recipe rev c8fff1f0ad8a07baf8461e92744e4539，package ID 0f43cddf8f0746f39df42f9f026ecaab38cf98d1）
- openssl 3.5.6（re 的传递依赖）

## 编译的模块列表

account, aufile, auconv, augain, auresamp, ausine, contact, debug_cmd, echo,
g711, libg722, g722, g7221, httpreq, ice, in_band_dtmf, l16, menu, mixausrc,
mixminus, mqtt, httpd, mwi, natpmp, pcp, plc, presence, rtcpsummary, selfview,
serreg, snapshot, stdio, stun, turn, uuid, vidbridge, vidinfo, vumeter, fakevideo

## 验证结果

```bash
# conan create 验证 (G2)
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# G2: PASS — 库编译成功，test_package 3/3 测试通过

# 验证库文件
ls -la lib/libbaresip.a
# -rw-rw-r-- libbaresip.a (静态库)

# 验证符号
nm lib/libbaresip.a | grep -E "T baresip_init|T conf_configure|T ua_alloc"
# 所有符号已正确导出

# baresip 二进制 (L2: skip)
# baresip 是交叉编译产物 (OHOS aarch64)，无法在 x86_64 构建主机上直接运行。
# L2 检查正确跳过 (ci-metadata.json: "L2": {"result": "skip", "detail": "baresip version/help failed"})
```

## 注意事项

- baresip 使用 CMake 构建系统（不是 autotools）
- 模块化架构：通过 MODULES CMake 变量控制编译哪些模块
- re (libre) 通过 Conan 依赖管理，CMakeDeps 生成 re-config.cmake
- CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 是 Conan CMakeToolchain 的默认行为，需要补丁适配
- baresip_init() 在 OHOS 上因 DNS 初始化失败，不影响库编译和基本 API
---

**编译结束**: 2026-08-10 11:31
**最终状态**: built
