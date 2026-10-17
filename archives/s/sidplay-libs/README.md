# sidplay-libs

C64 SID 音乐回放库集合（sidplay2 播放器所需的运行库）。

## 组件

| 库 | 说明 |
|----|------|
| libsidplay2 | SID 播放引擎（C64 周期精确立体声回放核心） |
| libsidutils | SID 工具库（SID 数据库、滤镜、曲调修改） |
| resid-builder | reSID 芯片模拟器 builder |
| hardsid-builder | HardSID 硬件 builder |

## 上游

- 官方源：SourceForge sidplay2 项目（`sidplay-libs-2.1.1.tar.gz`）
- 版本：2.1.1（与 sidplay 2.0.9 配套）

## OHOS 适配

- **config.guess/config.sub**：2004 年老版本不识别 HarmonyOS，打补丁输出 `aarch64-unknown-linux-ohos`（E007）
- **umask 022**：configure/config.status 的 mktemp 077 在 HMDFS setgid 目录不可写（E112）
- **C++11 兼容**：老代码 `int8_t` 数组窄化（xsid.cpp）、模板两阶段查找（SmartPtr.h `this->`）、多余类限定 operator=（SidUsage.h）
- **in-source 构建**：顶层 configure 是自定义递归脚本，硬编码相对路径，Conan 配方需 `folders.build="."`
- **静态库**（R26）：`--enable-static --disable-shared`，避免污染系统 /lib /lib64

## 产物

库类型（无可执行文件），无需 commands.json。
