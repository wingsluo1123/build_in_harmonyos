# wvkbd 0.15 适配笔记

## 编译环境

- 构建系统：CMake + Conan 2
- 编译日期：2026-10-16
- C 工具链：HarmonyOS/OpenHarmony clang 15，`armv8` / AArch64，C++ runtime libc++
- HarmonyOS 应用工具链：DevEco Studio 26.0.0 SDK；HAP 兼容与目标版本为 HarmonyOS 6.1.0 (API 23)
- 目标：HarmonyOS PC Stage 输入法扩展
- 上游源码：GitHub `jjsullivan5196/wvkbd`，v0.15，SHA-256 见 `conandata.yml`

## 路线选择

采用路径 C（高难度挑战）。上游程序紧密绑定 Wayland client 和虚拟键盘协议，没有可移植的输入/显示后端抽象；HarmonyOS 的系统输入法必须由 `InputMethodExtensionAbility`、IMEKit 和 ArkUI panel 承载。实现保留可复用的键盘布局和修饰键逻辑，重写平台输入、显示和会话集成。此工作符合高难度标准第 1 项，主要难点是系统接口和交互生命周期迁移。

同时以知识草稿作为路径 B 保底材料：`knowledge/drafts/E429-draft-D7A3.kv/.md` 记录 HarmonyOS 6.1 真机上输入客户端交接时可能没有 `inputStop` 回调的证据和验收方法。该草稿仍待知识库审核，不视作已合并条目。

## 架构与源码修改

- `harmonyos/core/`：实现字母/符号布局、Shift/Caps 状态、文本映射及状态重置；无 HarmonyOS 头文件，便于在 host CTest 与目标架构复用。
- `harmonyos/ime_app/`：用 `InputMethodExtensionAbility` 建立系统输入法服务；ArkUI panel 绘制键盘并读取真实组件 bounds；C NAPI adapter 调用同一个 C core。
- `test_package/ohos_test_app/`：独立编辑器 HAP 链接 Conan test consumer，通过用户交互验证键盘行为。
- 上游 Wayland/XKB/GTK（如有）输入显示链路不进入 HarmonyOS 产物；新增移植文件与适配实现均保留在归档目录，无上游测试修改、无平台宏补丁。

## 构建与测试

上游 v0.15 源码包无 `tests/`、`test/` 目录，无 `check`/`test` target，也未注册自动化测试。该结论来自 `test_package/MANIFEST.yml` 中的源码文件与 Makefile 清点。上游可计数自动用例为 0；适配后新增 8 个独立产品测试项：4 个 C core 项（C01–C04）及 4 个 HarmonyOS 设备项（D01–D04）。各 C 项在 host 与设备目标上的执行是重复执行同一测试项，不重复计数。另有 57 项 host harness pytest 检查，单独作为基础设施检查统计。

Conan 配方在 OHOS armv8/clang15 profile 下构建静态库；test_package 再构建 consumer 与 PIC consumer archive。系统 IME 和测试 editor HAP 均从当前 Conan package source files 组装，`wvkbd_DIR` 由测试 runner 注入 module 级 CMake arguments。

设备测试通过设置内建输入法、实际键入组合字符、检查 Done submit 与 Shift glyph，再切换真实 `TextInput` 并验证旧 panel/new token/Shift reset。完整最终结果、计数和清理证据见 `PORTING_REPORT.md`。

## 关键适配决策与问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 初次 HAP CMake 配置找不到 `wvkbdConfig.cmake` | 依赖路径被写入工程配置，而 Hvigor native task 读取 entry 模块配置 | runner 只在临时构建副本的 `entry/build-profile.json5` 中注入 Conan CMakeDeps 路径 |
| ArkTS 构建器不接受数组解构循环 | 当前 DevEco ArkTS 编译限制 | 使用索引读取坐标，保持相同 glyph 采样结果 |
| 默认拒绝缺 `inputStop` 的旧会话关闭 | HarmonyOS 6.1 真机完成 TextInput 焦点交接并销毁旧 panel，但未发出该 callback | 只接受真实 focus callback + old-token panel destroy + distinct new token/start/create/show；若系统发 stop，仍验证先于 destroy |
| Backspace 删除无效 | SDK 的 `InputClient.deleteBackward()` 删除光标后的字符；输入光标通常位于文本末尾 | 映射删除键到 `deleteForward(1)`（SDK 命名方向与通常直觉相反），并通过 D01/D02 真机输入与删除场景验证 |
| D04 后终态清理误报 | 同一 run 的重复 stop/focus 生命周期日志没有序号，runner 按 JSON 去重时吞掉第二次完全相同的记录 | lifecycle marker 带单调序号；editor 在收到 `d` 后同步请求焦点到第二个真实 TextInput，runner 预先记录清理边界并核验成功请求、焦点回调、旧面板销毁与新 token |
| 新会话先于旧 panel 销毁回调 | HarmonyOS 6.1 在最终输入焦点交接中先发出新 `inputStart`，再异步销毁旧 panel | 校验新的 start token 与 UI handoff 证据；要求旧 panel destroy 先于新 panel create/show，不把 start/destroy 的交错误判为失败 |
| 本机 HAP 构建报告找不到 SDK version | 开始时误把 SDK `default` 子目录当成 SDK 根；项目还沿用 modelVersion 6.0 | runner 使用 DevEco SDK 父目录，项目 modelVersion/compileSdkVersion 与安装的 SDK 26.0 对齐，HAP compatibility/target 保持 6.1 |
| CI #94927 在库的 CMake 配置前无法 fork | worker 的知识检查与杂项检查已多次报告进程创建失败；Conan 默认 `conanbuildenv-*.sh` 还会为恢复脚本逐个调用 `printenv` | 库配方和 test consumer 禁用 shell 环境激活文件，改用 `VirtualBuildEnv.vars().apply()` 将同一配置直接应用到 CMake 子进程；consumer 保留 `-j1` 限制。强制重建的本机 OHOS armv8 包及 consumer 均成功；远端 CI 待更新分支后重跑 |

## 本机验证命令

```powershell
conan create archives/w/wvkbd/0.15 --version=0.15 `
  -pr:h=<OHOS-armv8-clang15-profile> -pr:b=default --build=missing
```

设定 `WVKBD_HDC`、`WVKBD_SDK`、`WVKBD_HVIGOR`、`WVKBD_NODE`、`WVKBD_BASE_SDK` 和本地开发签名配置后，Conan test_package 会自动构建签名 HAP、连接 HDC 设备运行用例并在 `finally` 卸载临时 bundle。具体变量对应关系和隐私限制见 `test_package/README-harmonyos-device.md`。
