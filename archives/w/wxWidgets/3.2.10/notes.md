# wxWidgets 3.2.10 编译笔记

## 编译信息
- **软件**: wxWidgets 3.2.10
- **日期**: 2026-05-29
- **构建系统**: CMake
- **状态**: built

## 编译步骤

### 1. 源码获取
```bash
git clone https://github.com/wxWidgets/wxWidgets.git --depth 1 --branch v3.2.10
```

### 2. 平台适配
修改 `build/cmake/toolkit.cmake`，添加 HarmonyOS 平台检测：
```cmake
elseif(CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS|OpenHarmony)$")
    set(wxDEFAULT_TOOLKIT gtk3)
    set(wxTOOLKIT_OPTIONS gtk2 gtk3 gtk4 motif qt)
    set(wxPLATFORM UNIX)
```

wxWidgets 的 `build/cmake/setup.cmake` 已通过编译测试探测 socket 能力：
`WX_SOCKLEN_T`、`SOCKOPTLEN_T`、`HAVE_GETHOSTBYNAME`、
`HAVE_GETHOSTBYNAME_R`、`HAVE_GETSERVBYNAME` 和 `HAVE_INET_ATON`。
适配不定义平台专用能力宏，避免对不同 HarmonyOS libc 版本作硬编码假设。

### 3. CMake 配置
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DwxBUILD_SHARED=OFF \
-DwxBUILD_TESTS=OFF \
-DwxUSE_GUI=OFF \
-DwxUSE_XLOCALE=OFF \
-DwxUSE_ZLIB=builtin \
-DwxUSE_REGEX=builtin \
-DwxUSE_EXPAT=builtin \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++
```

### 4. Socket 能力检测

不修改 socket C++ 源码。CMake 配置阶段使用 wxWidgets 上游已有的
`wx_get_socket_param_type()`、`check_symbol_exists()` 和
`check_prototype_definition()`，根据目标 sysroot 的头文件和链接能力生成
`wx/setup.h`，自动选择 socket 长度类型、标准 resolver 函数及可用的 `_r` 变体。

### 5. 编译与安装
```bash
cmake --build . -j2
cmake --install . --DESTDIR=$TEST_PREFIX
```

---

**编译结束**: 2026-05-29

**最终状态**: built

**产物**:
- libwx_baseu-3.2.a (核心库)
- libwx_baseu_net-3.2.a (网络库)
- libwxregexu-3.2.a (正则库)
- libwxexpat-3.2.a (XML 解析库)
- libwxzlib-3.2.a (压缩库)

**补丁**: 0001-harmonyos-socket-fix.patch
