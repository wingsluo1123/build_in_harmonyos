# Progress PC1 — 阻塞待复核队列转进行中队列

## 本轮选择

- [x] re(依赖项) 4.9.0 — 复核通过，OpenSSL 头文件存在，开始完整适配
- [x] baresip 4.9.0 — 依赖链完整，待 re 完成后开始适配
- [ ] bluetoothconnector 2.1.0 — 阻塞确认：macOS 专用蓝牙工具
- [ ] chisel 2.0.1 — 阻塞确认：iOS/macOS LLDB 调试工具
- [ ] libewf 20240506 — 阻塞确认：HMDFS config.guess 临时文件创建失败
- [ ] lld@21 21.1.8 — 暂缓：等待 LLVM/SDK 问题明确

## 总览

| 处理 | 库名 | 版本 | 状态 | 链接 |
|------|------|------|------|------|
| [x] | re(依赖项) | 4.9.0 | 进行中：完整适配中 | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/933 |
| [x] | baresip | 4.9.0 | 等待 re 完成 | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/916 |

## 已复核阻塞项（本轮不处理）

| 库名 | 版本 | 阻塞原因 | 链接 |
|------|------|---------|------|
| bluetoothconnector | 2.1.0 | macOS 专用蓝牙工具，HarmonyOS 不适用 | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/918 |
| chisel | 2.0.1 | iOS/macOS LLDB 调试工具，HarmonyOS 不适用 | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/920 |
| libewf | 20240506 | HMDFS config.guess 无法创建 dummy.c (Permission denied) | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/922 |
| lld@21 | 21.1.8 | 暂缓：等待 LLVM/SDK 问题明确 | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/925 |

## PR 跟踪

### re(依赖项) 4.9.0

| 阶段 | 状态 | 备注 |
|------|------|------|
| recipe 创建 | ⏳ | |
| 本地 finish | ⏳ | |
| submit / PR | ⏳ | |
| 远端 CI | ⏳ | |
| AI Review | ⏳ | |
| 评审闭环 | ⏳ | |
| 等待人工审核 | ⏳ | |

### baresip 4.9.0

| 阶段 | 状态 | 备注 |
|------|------|------|
| recipe 创建 | ✅ | conanfile.py + conandata.yml + test_package + patches |
| 本地 finish | ❌ | 阻塞：CMake FindPkgConfig 兼容性 bug + 链接 OpenSSL 符号问题 |
| submit / PR | ⏳ | 等待 finish 通过 |
| 远端 CI | ⏳ | |
| AI Review | ⏳ | |
| 评审闭环 | ⏳ | |
| 等待人工审核 | ⏳ | |

#### 阻塞证据

baresip 4.9.0 在 OHOS 上 `conan create` 失败，根因：
1. **CMake FindPkgConfig 兼容性 bug**：`FindSNDFILE.cmake` 调用 `pkg_check_modules` 时触发 CMake 4.1.2 的 `if` 参数解析错误
2. **链接 OpenSSL 符号问题**：`libbaresip.so` 通过 re 库间接依赖 OpenSSL，链接器 `--no-allow-shlib-undefined` 阻止未定义符号通过
3. **CMake OHOS 平台检测不完整**：`CMAKE_SYSTEM_NAME=Linux` 绕过检测但引入 Linux 专用源文件冲突

修复方向：需等待 CMake 工具链更新或手动 patch CMake FindPkgConfig 模块。当前标记为 `阻塞`。|