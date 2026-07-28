# ipsumdump 1.86 — 适配记录

## 编译过程

### 编译系统
- 构建系统: Autotools (configure + make)
- 编译器: clang 15.0.4
- 依赖: libpcap/1.10.6 (published)

### 补丁列表
| 补丁 | 说明 | 类型 |
|------|------|------|
| 0001-config.guess-ohos.patch | config.guess HarmonyOS 识别 (E007/E072) | portability |
| 0002-config.sub-ohos.patch | config.sub OHOS 三元组 + aarch64 (E007/E072) | portability |
| 0003-siocgstamp-ohos.patch | SIOCGSTAMP fallback for OHOS arm | portability |

内联补丁 (conanfile.py build()):
- umask 077→022 (E002/E011, HMDFS)
- Linux检测强制通过 (libclick configure)
- _IOC_DIRSHIFT 回退定义 (llrpc.h)
- install-man 禁用 (HMDFS 路径)

### 测试结果
- test_package: 1/1 通过 (100%)
- 上游测试: 0/0 (N/A)
- W3本地CI: 通过

## 最终状态
status: closed
