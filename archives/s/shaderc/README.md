# shaderc

Google 的着色器编译工具集：`libshaderc` 库 + `glslc` 命令行，把 GLSL/HLSL 编译为 SPIR-V。

- 上游：https://github.com/google/shaderc
- 许可证：Apache-2.0
- 语言：C++（主体），构建系统 CMake（ninja 生成器）
- 依赖：无外部 conan 包；glslang / SPIRV-Tools / SPIRV-Headers 随源码树同源构建，
  三者的提交由上游 `DEPS` 文件固定，配方按同源提交拉取并还原 `third_party/` 布局

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 2026.3 | built | arm64 适配（详见 2026.3/notes.md） |

## 平台说明（OHOS）

- 交付物：`libshaderc` 系列静态库（`libshaderc.a` / `libshaderc_util.a` / `libshaderc_combined.a`）
  与 `glslc` 命令行；`glslc` 仅依赖 `libc++_shared.so` 与 `libc.so`，可在 OHOS arm64 直接运行
  （`glslc --version` 与 GLSL→SPIR-V 编译实测通过）
- 上游 `SOVERSION` 在 OHOS 不生效（CMake 4.x 无 `Platform/HarmonyOS.cmake` 模块），
  `libshaderc_shared.so` 无版本后缀且无 `DT_SONAME`；本包声明为 `static-library`，
  故不交付该共享库（详见 2026.3/notes.md「三、OHOS 适配点」）
