# DRAFT：Conan 空 generic_system 块 → PROCESSOR=unknown → 上游架构分发静默编入异架构桩 DSO

> Status: **Draft**（待审核 promote，最终编号 Exxx 由知识主编回填；drafts 内 id 禁用数字编号——已有两个 DRAFT-8959-* 撞号先例）
> severity: `2` | category: `platform|detection|cmake|conan|build-system`
> 对应 kv: `knowledge/drafts/DRAFT-conan-generic-system-empty-arch-dispatch-stub.kv`（字段派生自 kv，两者成对维护）

---

## 触发面

- trigger_tool: `conan|cmake`
- phase: `configuration|build|runtime`

**匹配关键词**：CMAKE_SYSTEM_PROCESSOR, generic_system, CMakeToolchain, user_toolchain,
Building for unknown architecture, ENABLE_SW_ARCH, sw_64, swImpl, stub, arch dispatch,
uname -p, unknown, aarch64, NOT_SUPPORTED

## 错误签名（error_signature）

```text
Building for unknown architecture|src/swImpl/.*\.obj|StatusCode\(\) == NOT_SUPPORTED(?!.*grpc)|vector_client_smoke.*Failed [0-9]\.[0-9]+ sec
```

三者组合定位：configure 期 STATUS 行 + 构建清单中的异常架构实现文件 + 运行期返回码/冒烟失败时长。
单独的 "System is unknown to cmake" **不可**作签名——E545 已证其在"上游不消费
CMAKE_SYSTEM_PROCESSOR"的多数场合是良性告警。

## 根因（完整因果链）

1. conan 2.29.1 CMakeToolchain 在 host==build 原生构建下 `_get_generic_system_name()`
   不返回系统名 → **generic_system 块渲染为空**（工具实现语义，参照 DRAFT-E622 记载），
   `conan_toolchain.cmake` 不设 `CMAKE_SYSTEM_NAME`/`CMAKE_SYSTEM_PROCESSOR`。
2. `project()` 时 CMakeDetermineSystem 走宿主分支：`uname -s=HarmonyOS` 无
   `Platform/HarmonyOS.cmake` 仅告警；`CMAKE_SYSTEM_PROCESSOR` 取自 `uname -p`，
   本机该**命令成功执行但返回字符串 `"unknown"`**（`uname -m` 正常返回 `aarch64`；
   "uname 失败/unavailable" 的表述不准确，勿沿用）。
3. 上游 `CMakeLists.txt:25` `if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|aarch64")` 失配 →
   `else()` 分支 `add_definitions(-DENABLE_SW_ARCH)` 仅编 `src/swImpl/`（STATUS 行
   "Building for unknown architecture" + `SwClientImpl.cpp.obj` 进入构建清单）。
4. configure rc=0、build rc=0，失败后移至运行期：工厂返回桩实现，全部 API 返回
   `NOT_SUPPORTED`（消费者冒烟 0.04–0.05s FAIL 是唯一可见症状）。
5. 归类：**平台探测语义差异 × 上游架构/后端分发静默落错分支**。

关键机理补充：仅注入 `CMAKE_SYSTEM_PROCESSOR` 不够——宿主分支仍会覆写它（实测复现）；
必须同时注入 `CMAKE_SYSTEM_NAME` 使 CMakeDetermineSystem 走交叉分支、尊重工具链的
PROCESSOR 值。

## 影响范围（affected_scope）

任何经 conan CMakeToolchain 在 OHOS 设备原生构建、且上游 CMake 按
`CMAKE_SYSTEM_PROCESSOR` 做架构/后端分发的项目（gRPC/milvus 系客户端多后端实现选择、
SIMD 分发、按处理器门控的组件族）。伴生信号面：configure 期 STATUS 行
`Building for <processor> architecture` 与构建清单中异常架构实现文件是仅有的可见线索；
configure/build 全绿不构成适配成功证据，须 STATUS 行清点 + 交付面符号对照 + 行为断言
三重验证。

## 推荐方案

**方法**: `user_toolchain-preinject-system-name-processor`

配方 `generate()` 以 `conan.tools.files.save` 写两行片段并通过
`tools.cmake.cmaketoolchain:user_toolchain` 注入（该块在 conan_toolchain.cmake 中
**最先渲染**）：

```cmake
set(CMAKE_SYSTEM_NAME HarmonyOS)      # 真实系统名——切入 CMakeDetermineSystem 交叉分支
set(CMAKE_SYSTEM_PROCESSOR aarch64)   # 与 profile arch 对应的目标处理器
```

```python
save(self, os.path.join(self.generators_folder, "ohos-system-processor.cmake"),
     "set(CMAKE_SYSTEM_NAME HarmonyOS)\nset(CMAKE_SYSTEM_PROCESSOR aarch64)\n")
self.conf.define("tools.cmake.cmaketoolchain:user_toolchain", [<片段路径>])
```

CMakeDetermineSystem 见 `CMAKE_SYSTEM_NAME` 非空走交叉分支、尊重工具链 PROCESSOR 值 →
`project()` 见 `aarch64` → 上游门控命中真实现分支。`CMAKE_SYSTEM_NAME=HarmonyOS` 是
真实系统名（能力探测，非 Linux 冒充）。两行缺一不可。

**等价形**：`tc.blocks["generic_system"].values` 直接赋值（pybind11 草稿先例），同样要求
在 CMakeToolchain 渲染前就位。

**验证**：configure 输出 `grep 'Building for aarch64 architecture'` 命中；构建清单无
`src/swImpl/` 条目；交付 `.so` `nm -D` 含真实现符号；消费冒烟断言
`Status.Code() != NOT_SUPPORTED`。

## 回退（fallback）

1. 补丁把上游 `else()` 桩分支改为
   `message(FATAL_ERROR "unsupported processor: ${CMAKE_SYSTEM_PROCESSOR}")`——
   把静默错误显式化。诚实权衡：不解决适配，只保诊断，杜绝桩 DSO 冒充交付物。
2. apache-arrow 先例（同族探测落空时给门控正则加 `|unknown` 后缀）：仅当 profile
   固定目标架构、`unknown` 必然等价于目标架构时可用。权衡：掩盖探测缺陷而非修复，
   跨平台配方不可移植，明记为退路并记录技术债。

## 禁止事项（forbid）

| 禁止 | 原因 | 后果 |
|---|---|---|
| 将桩分支（`ENABLE_SW_ARCH`/`swImpl`）DSO 作为适配产物交付 | 桩实现全部方法返回 NOT_SUPPORTED，不构成适配，只是把失败后移到运行期 | 消费者拿到假实现，功能静默失效，集成后排障成本指数放大 |
| 据 E545 对 "System is unknown to cmake" 一律放过、不检查上游是否消费 CMAKE_SYSTEM_PROCESSOR | E545 良性结论有"上游不消费 PROCESSOR"前提；上游按处理器分发时该告警伴生静默错分支 | 异架构桩被静默编入产品，configure/build 全绿掩盖失败 |
| `-DCMAKE_SYSTEM_NAME=Linux` 冒充（不声明权衡） | E532 forbid 同源：污染上游系统名分支判定；HarmonyOS 本就是真实系统名 | 上游按系统名区分的宏、路径、特性探测误走 Linux 路径，问题后移 |

## 自包含验证（verification_cmd）

```sh
uname -p                                   # → unknown（命令成功，退出码 0）
mkdir -p /tmp/arch-probe && cd /tmp/arch-probe
printf 'cmake_minimum_required(VERSION 3.20)\nproject(p C)\nif(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|aarch64")\n  message(STATUS "Building for target arch")\nelse()\n  message(STATUS "Building for unknown architecture")\nendif()\n' > CMakeLists.txt
cmake -B build 2>/dev/null | grep 'Building for'    # → unknown architecture，rc=0（静默选中桩分支）
printf 'set(CMAKE_SYSTEM_NAME HarmonyOS)\nset(CMAKE_SYSTEM_PROCESSOR aarch64)\n' > fix.cmake
cmake -B build-fix -DCMAKE_TOOLCHAIN_FILE=fix.cmake 2>/dev/null | grep 'Building for'   # → target arch
# 交付面对照 + 行为断言：
nm -D --defined-only lib*.so | grep -c <真实现符号>   # 真实现 >0，桩 =0
# 消费冒烟：工厂后首 API 断言 Status.Code() != NOT_SUPPORTED
```

## 关系

- principles: P004, P005
- similar_to: DRAFT-cmake-host-gate-silent-skip（同机 uname -p=unknown 已记载，但其后果是
  "组件静默缺席"、正则族是 SYSTEM_NAME 宿主门——本条后果是"异架构桩编入产品"、
  正则族是 PROCESSOR 架构分发）, E092, E532, E100, E545（良性结论的适用边界反例）,
  DRAFT-E622（空块机理：_get_generic_system_name 不返回系统名；其后果记载为
  "无 SONAME"，本条为其另一后果面）

---

*来源事件：libkysdk-vector-engine-client 1.2.0.0（gitee openkylin）HarmonyOS PC 原生
适配——上游 CMakeLists.txt:24-25 按处理器门控真实现/sw_64 桩；conan 2.29.1 空
generic_system 块 → PROCESSOR=unknown → 桩 DSO（R1/R2 消费冒烟 0.04-0.05s FAIL 为唯一
症状）；user_toolchain 前置注入后 R3 全绿。本文件由 kv 字段派生，内容与 kv 一致，
待主编审核 promote 后转入 knowledge/doc/。*
