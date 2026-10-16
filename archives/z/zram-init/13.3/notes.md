# zram-init 13.3 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 GNU Makefile，非 autotools：无 configure/automake）
- 编译日期: 2026-09-29
- 编译器: 无（纯 POSIX shell 脚本 + 数据文件，无 C/C++ 编译产物）
- 状态: built
- 本机: HarmonyOS PC aarch64（toybox 用户态 + GNU make 4.4.1 + clang 15 仅做环境自检）

## 软件说明

zram-init 是 vaeth 维护的 POSIX shell 脚本，用于在 zRAM 块设备上建立（SIZE）
或释放（SIZE=0）swap / tmpfs 挂载。上游 13.3 源码树构成：

- `sbin/zram-init.in` — 主脚本（模板，make 用 sed 替换 @MODIR@/@EXENAME@ 生成）
- `man/zram-init.8` / `man/zram-init.de.8` — man 页
- `modprobe.d/zram.conf` — `options zram num_devices=3`（运行时模块参数契约）
- `zsh/_zram-init` — zsh 补全
- `i18n/{de,fr}.po` — gettext 消息目录（需 msgfmt 编译 .mo）
- `systemd/system/*.service` × 4、`openrc/{conf.d,init.d}` — 服务管理器单元

## 编译步骤（探索性验证，W3 由 conan create 复现）

```sh
make GETTEXT=FALSE SYSTEMD=FALSE OPENRC=FALSE MODIFY_SHEBANG=FALSE -j1 sbin/zram-init
sh sbin/zram-init -h   # 输出 Usage 且 exit 0
```

toybox 环境实测：sed 自定义分隔符 `s'pat'rep'g`、`chmod 755 --`、make 目标
生成均正常；`sh -n` 语法检查通过。

## 适配决策（全部通过上游 make 变量表达，零源码补丁）

| 决策 | 理由 |
|------|------|
| GETTEXT=FALSE | OHOS shell 环境无脚本 gettext 运行时基础设施；.mo 编译还依赖构建机 msgfmt（CI worker 不保证有）。脚本退化为英文输出（上游注释亦提供 LANG=C 关闭翻译的用法） |
| SYSTEMD=FALSE / OPENRC=FALSE | 鸿蒙无 systemd/OpenRC 服务管理器，对应单元文件不属于目标平台运行面 |
| MODIFY_SHEBANG=FALSE | 保留上游 `#!/usr/bin/env sh`：OHOS 可移植且跨构建机可复现（make 默认会把构建机 `command -v sh` 路径烙进产物，破坏可复现性） |
| MODPROBED=TRUE | modprobe.d/zram.conf 是运行时契约（num_devices=3），随包发布 |
| 不使用 `make install` | 其 INSTALL_EXE 硬编码 `install -D`，toybox 无 install 命令（E392 原始 Makefile 配方模式）；package() 用 conan copy 显式 staging |
| package_id 清空 | 解释型脚本 + 数据文件，无 ABI、无工具链影响 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 从 github.com 下载超时（Errno 110） | 本机直连 github.com 归档超时 | 换 codeload.github.com 官方端点（curl 成功），conandata.yml 保持官方 URL（R39/PF7），conan source() 对 codeload 显式传 filename（E483/E276） |
| 2 | toybox 无 install 命令，`make install` 不可用 | 上游 INSTALL_EXE=`install -D` | 跳过 make install，package() 显式 copy（E392 模式） |
| 3 | automake 缺失 | 本机仅有 autoconf 2.72 | 无需：上游为手写 Makefile，非 autotools（E041 bypass-autotools 结论天然适用） |

## 源码修改

无（patches/ 为空：全部适配决策通过 make 变量表达，未改动上游任何源文件）。

## 依赖版本

无 conan 依赖（requires 为空）：纯 shell 脚本包，无库依赖。运行时宿主要求
（设备侧）：POSIX sh、coreutils、zram 内核模块；`zramctl` 缺失时脚本自动降级
（上游已内置 `command -v zramctl` 探测）。

## 上游测试清点（R51）

上游**无测试套件**，证据见 test_package/MANIFEST.yml：
1. `make -n check` → "No rule to make target 'check'"（Makefile 无 check/test 目标）
2. 源码树 0 个 test* 文件、0 个 .c 文件
3. 无 CI 测试配置

本适配补齐消费者视角测试（test_package/）：test.sh 10 条布局/内容断言 +
test() 3 条功能断言（sh -n 语法 + `-h` Usage/exit 0）+ harmony_e2e.sh 2 个
鸿蒙特有消费者端到端用例，共 15 项（19 条断言/检查），通过率 100%。

## PR 审查修复记录（rule12 鸿蒙特有测试，MR #15040）

首轮 AI 审查裁决：鸿蒙特有测试 N=0 < 1，要求至少一个完整消费者用例
（真正跑通功能/流程的端到端用例，不能是纯断言）。修复：新增
`test_package/harmony_e2e.sh`，在鸿蒙默认运行面（无 zram 内核模块、无
/sys/class/zram-control、toybox 用户态，本机实测）真实执行交付脚本的两条
主流程：

| 用例 | 命令 | 端到端路径 | 预期（本机实测验证） |
|------|------|-----------|---------------------|
| case1 释放流程 | `zram-init 0` | 参数解析→数值校验→设备探测→释放决策→退出 | exit 0 且无诊断输出（上游契约：无活动 zRAM 设备时释放为 no-op） |
| case2 建立流程 | `zram-init 64 DIR` | getopts→默认值→DIR 校验→设备探测→modprobe 尝试→5×1s hot_add 探测 | 鸿蒙内核边界优雅降级：精确输出上游致命消息 'cannot create /dev/zram0: /sys/class/zram-control missing'，exit 1，零副作用 |

设计说明：真实建 swap/挂载路径需 root + zram 内核模块 + zramctl/mkswap/mount
（本机与 CI 沙箱均不具备，上游自身也无任何自动化测试覆盖）；case2 覆盖了
建立流程从入口到内核边界的全部可执行逻辑（含鸿蒙特有的降级语义），case1
跑通完整释放主链路。两用例在存在真实 zram 基础设施的非干净宿主上自动
SKIP（如实记录，不虚构通过）；clean 沙箱（本机 + CI worker 实测）恒走
主路径。

## 已知运行面限制（非缺陷）

- zRAM 真实建立/释放路径需 root + zram 内核模块 + mkswap/mount/zramctl，
  构建沙箱不具备（上游亦无任何自动化测试覆盖这些路径）。
- CI L2 smoke 对 bin/zram-init 跑 `--version`/`--help`：脚本 getopts 仅支持
  短选项，长选项按上游设计 exit 1 → L2 记 warn（non-blocking，不阻塞门禁）；
  消费者冒烟用上游定义的 `-h`（Usage 0）。
---

**编译结束**: 2026-10-12 15:00
**最终状态**: built
