# HarfBuzz

HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。广泛应用于 Firefox、Chrome、Pango、Flutter 等项目。

- **Homepage**: https://harfbuzz.github.io/
- **License**: MIT
- **Build System**: CMake (推荐) / Meson / Autotools
- **Category**: gfx (字体/文本渲染)

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 14.2.0.1 | built | 2026-07-30 | CMake 重写，含 graphite2 支持 |
| 14.2.0 | archived | 2026-07-22 | Meson 构建（已废弃） |

## OHOS 适配要点

1. **构建系统**: 使用 CMake（meson 在 HMDFS 上有 subprocess 限制）
2. **graphite2 支持**: CMake 选项 `HB_HAVE_GRAPHITE2=ON`，依赖 graphite2/1.3.14
3. **freetype 支持**: CMake 选项 `HB_HAVE_FREETYPE=ON`，依赖 freetype/2.14.3
4. **静态编译**: `BUILD_SHARED_LIBS=OFF` (R5/R26)
5. **禁用特性**: glib/icu/cairo/gobject 不可用，`HB_BUILD_UTILS=OFF` 不构建工具
6. **头文件路径**: `package_info()` 需设置 `includedirs = ["include/harfbuzz"]`
7. **传递依赖**: `package_info()` 需设置 `cpp_info.requires = ["graphite2::graphite2", "freetype::freetype"]`
8. **test_package**: 必须使用 C++ (test.cpp)，因为 harfbuzz 和 graphite2 是 C++ 库

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| graphite2 | 1.3.14 | Conan (ohpcd) |
| freetype | 2.14.3 | Conan (ohpcd) |

WSL Clang 15 近似验证中，上游 59/59 组测试与消费者 shaping 流程均通过；真实 HarmonyOS 结果以 CI 为准。

PR #2906 的首轮 Build #7523 已完成编译并执行上游套件，结果为 56 通过、2 个 LLVM 工具启动失败、1 跳过。配方改为向原测试注入工具绝对路径后，Build #7546 在对应 HEAD 上通过全部 CI 步骤；归档工具版本后缀统一后的 HEAD `6de3ea24626b8b0b00feebd494289aa8e039fa23` 又由 Build #7584 验证通过。第三轮 Review 要求的签名命令路径 quoting 已在本地落实，推送后仍须以新 HEAD 的正式 CI 为最终证据。

## 参考
- 官网: https://harfbuzz.github.io/
- 源码: https://github.com/harfbuzz/harfbuzz
