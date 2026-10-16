# ir_keytable 1.32.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-10-02
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos, OHOS 交叉)
- 状态: published

## 编译步骤

1. meson 交叉编译 v4l-utils（OHOS aarch64）：MesonToolchain 自动注入交叉参数（host_machine=linux+musl, sysroot）。
2. 禁用所有与 ir-keytable 无关的可选组件，最小化构建面：bpf/gconv/jpeg/libdvbv5/qv4l2/qvidcap/v4l2-tracer/v4l-plugins/v4l-wrappers/v4l2-compliance-libv4l/v4l2-ctl-* /doxygen-* 全部 disabled，仅保留 v4l-utils=True。
3. argp 注入：OHOS(musl) 无 glibc argp → 依赖 argp-standalone/1.5.0；其 cpp_info.includedirs/libdirs 已是绝对路径，直接 -I/-L/-l 注入（不可再拼 package_folder，否则路径翻倍致链接器找不到 -largp）。
4. 移除 -DENABLE_NLS：common_arguments 的 NLS 宏在 build() 移除，源码 #else 分支 `_()=string` 兜底，无需 libintl（libintl .so 为薄桩含未定义符号，不可用）。
5. patch meson machine 文件：`_patch_meson_machine_files()` 修正 meson 的 host_machine 三元组识别（OHOS 交叉场景）。
6. 签名 ELF：`_sign_ohos_package_elfs()` 用 `binary-sign-tool sign -selfSign 1` 对产物 ELF（ir-keytable）自签（HarmonyOS MAC 拒绝执行未签名 ELF）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接器找不到 -largp | OHOS(musl) 无 glibc argp，meson `cc.find_library('argp')` 搜不到 | 依赖 argp-standalone/1.5.0，-I/-L/-l 显式注入（用 cpp_info 绝对路径，不拼 package_folder） |
| 2 | libintl 不可用 | libintl .so 为薄桩含未定义符号 | 移除 -DENABLE_NLS，源码 #else 分支 `_()=string` 兜底 |
| 3 | meson 不识别 OHOS 三元组 | 交叉三元组 aarch64-linux-ohos 非标准 | `_patch_meson_machine_files()` 修正 host_machine 识别 |
| 4 | ELF 执行 Permission denied | HarmonyOS MAC(hmmac) 拒绝未签名 ELF | `binary-sign-tool sign -selfSign 1` 自签 |

## 源码修改

无补丁（路径 A 基础适配，conandata.yml 指向官方 linuxtv.org 源码；meson/OHOS 适配全在 conanfile.py 的 generate()/build() 完成，不改上游源码）。

## 上游测试清点（R51）

- 上游 meson 构建**未为 keytable 注册任何测试**：v4l-utils 1.32.0 的 meson.build 中 ir-keytable 目标无 `test()` 注册，meson 测试目录无 keytable 相关用例 → **上游 keytable 测试用例数 = 0**。
- 历史 autotools 的 check 目标（rc_keymap 数据校验）**未迁移至 meson**（meson 化时丢弃）。
- 清点证据：meson 无 keytable test 注册 + 无 keytable 测试源文件。
- 结论：上游 0 用例，适配后补全 3 项 consumer 侧实质执行断言（可执行性/--version/--help）。

## 依赖版本
- argp-standalone/1.5.0（host 依赖，替代 musl 缺失的 glibc argp）
- meson/1.11.0（build_requires，交叉构建工具）

## 验证结果

```bash
# conan create（G2 门禁，含 test_package）
conan create archives/i/ir_keytable/1.32.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 结果: conan-verify 8 道门禁全过 (G0-G4 + L2/L4/L5), Pass rate 100%

# test_package 实跑（test_ir_keytable.sh，4 项含 [PROBE] 探测）
ir-keytable --version   # → ir-keytable 1.32.0
ir-keytable --help      # → 含 Usage / keytable 帮助文本
```

## 鸿蒙特有测试与硬件限制（rule12）

ir-keytable 为硬件依赖工具（红外遥控 keytable 配置），核心 IR 功能（IR 解码/键表管理）依赖物理 rc 设备（/sys/class/rc/）+ 实际 IR 信号。

### 源码实证（keytable.c，sha256 与 conandata 一致）
- `find_device()`（L896-907）只遍历 `/sys/class/rc/`（L904 `snprintf(dname, "/sys/class/rc/")`）；uinput 虚拟 input 设备在 `/dev/input/eventX`，不在其中 → ir-keytable 无法发现 uinput 虚拟设备（方案 B 不可行）。
- `test_event()`（L1519-1630，`-t`）为无限循环 `while(1)` + `poll(...,-1)` 无超时 → CI 上会阻塞，无法用作测试。
- 无设备时所有实质功能（read/write/clear/test/protocol）均 `find_device` 失败 → exit -1。
- 1.32.0 无 `--check-rc-map`/`--print-protocols` 等无设备命令（选项表 L263-280 确认）。

### [PROBE] 设备探测结果
`test_ir_keytable.sh` 开头加 [PROBE] 探测（只收集信息不影响 pass/fail）：
- 本地鸿蒙 PC aarch64（HongMeng Kernel 1.12.0）：`/sys/class/rc/` 不存在、`/dev/uinput` 不存在、`/dev/input/event*` 无权限。
- CI worker（#91012 PASSED）：探测测试正常工作，结果在 CI 日志（评审可见）。
- 结论：本地 + CI worker 均无物理 rc 设备、无 uinput → 核心 IR 功能无法端到端验证。

### 鸿蒙特有测试定位
"鸿蒙 PC 平台适配验证"（[PROBE] 设备能力探测 + 可执行性 + --version/--help），系无硬件环境下可验证的上限，非核心 IR 功能端到端。申请 rule12 硬件工具豁免。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ir-keytable | IR 遥控 keytable 配置工具（已自签 ELF） |

## 注意事项
- OHOS(musl) 环境无 glibc argp，必须用 argp-standalone 替代；argp cpp_info 路径已是绝对路径，注入时不可再拼 package_folder。
- 移除 ENABLE_NLS 后依赖源码 #else 兜底，若上游改 NLS 宏结构需重新评估。
- 产物 ELF 必须自签（binary-sign-tool -selfSign 1），否则 HarmonyOS MAC 拒绝执行。
---

**编译结束**: 2026-10-02 21:28
**最终状态**: published
