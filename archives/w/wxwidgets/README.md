# wxWidgets

## 软件简介
wxWidgets 是一个跨平台的 C++ GUI 工具包，提供丰富的 GUI 组件和网络功能。

**重要限制**：在鸿蒙系统上，wxWidgets 不支持 GUI 功能（GTK/X11/Wayland 不可用），只能构建 **base toolkit**（基础库），提供：
- 字符串处理
- 文件系统操作
- 网络功能（socket、HTTP、FTP）
- 正则表达式
- 多线程
- 配置管理
- 数据序列化

## 版本信息

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|---------|------|
| 3.2.10 | built | cmake | base toolkit（无 GUI） |

## 安装使用

### 预编译包安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- wxwidgets 3.2.10
```

### CMake 集成
```cmake
find_package(wxWidgets REQUIRED)
target_link_libraries(your_target wx::base wx::net)
```

### wx-config 使用
```bash
wx-config --version    # 输出：3.2.10
wx-config --libs       # 输出链接选项
wx-config --cxxflags   # 输出编译选项
```

## 关键依赖
- zlib/1.3.1
- expat/2.6.0
- curl/8.19.0（可选，用于 wxWebRequest）

## 编译说明

### CMake 配置选项
```bash
cmake <source_dir> \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DwxUSE_GUI=OFF \
  -DwxBUILD_SHARED=OFF \
  -DwxBUILD_SAMPLES=OFF \
  -DwxBUILD_TESTS=OFF
```

### 关键注意事项
1. **必须设置 `wxUSE_GUI=OFF`**：鸿蒙不支持 GTK/X11
2. **LD_LIBRARY_PATH**：需包含 OHOS SDK 的 lib 目录
3. **静态库推荐**：避免 ELF 签名问题

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libwx_baseu-3.2-OHOS.a | 6.5MB | wxWidgets 基础库（静态） |
| libwx_baseu_net-3.2-OHOS.a | 977KB | wxWidgets 网络库（静态） |
| libwxregexu-3.2.a | 364KB | wxWidgets 正则表达式库（静态） |
| wx-config | 47KB | 配置工具 |
| wxWidgetsConfig.cmake | 7KB | CMake 配置文件 |

## 参考资料
- 官方网站：https://www.wxwidgets.org/
- CMake 构建文档：https://docs.wxwidgets.org/3.2/page_cmake.html
