# erfa 2.0.0 适配笔记

## 基本信息
- 构建系统: meson（**以补丁新增**，见下）
- 源码: https://github.com/liberfa/erfa/archive/refs/tags/v2.0.0.tar.gz
- SHA256: e40f5175604c50c46fded7f9f76565dd5879a7f4ee27fa4484c2af217b7dfeb4
- 编译日期: 2026-10-15
- 编译器: clang（OHOS llvm 工具链，aarch64-linux-ohos）
- license: BSD-3-Clause
- 状态: built

## 与 2.0.1 的关键差异（本 run 的核心适配点）

**上游 2.0.0 没有 meson.build**——meson 支持是 v2.0.1 才加入的，因此 2.0.1
配方的"开箱即用 meson"路线不能照搬。本版本的三条候选路线权衡：

| 路线 | 结论 |
|------|------|
| (a) recipe 以 patches/ 新增最小 meson.build（根+src），逻辑参照上游 v2.0.1 tag | **采用**。与 2.0.1 配方形态一致；meson 在本设备已被 2.0.1 验证可用；绕开 HMDFS autotools 全部坑 |
| (b) autotools 路线 + E112/E114/E118 绕行 | 放弃。需 sed 改 configure/config.status 临时目录逻辑（知识 E112/E114/E118 的 rec_command 均为手工 sed/patch 脚本），脆弱且补丁面大 |
| (c) 直接 clang 编译 src/*.c + ar | 放弃。需自写 install 规则、版本宏注入、pkgconfig 与测试驱动，偏离仓库既有 meson 配方形态，且无上游测试注册机制 |

补丁 `patches/0001-add-minimal-meson-build.patch` 仅新增 2 个文件：
- `meson.build`（根）：project version 2.0.0；libtool 版本 [9,0,8]（来自 2.0.0
  configure.ac 的 `ERFA_LIB_VERSION_INFO(9,0,8)`，注意 2.0.1 是 [9,1,8]）；
  `SOFA_VERSION '20210512'`（2.0.1 为 20231011）；PKG_VERSION 三段拆分注入
  confdata；pkgconfig 生成。
- `src/meson.build`：249 个库源文件清单（与上游 v2.0.1 meson 清单逐文件比对
  一致，2.0.0→2.0.1 无源文件增删）；`configure_file(config.h)` + 
  `-DHAVE_CONFIG_H`（erfaversion.c 依赖其 PACKAGE_VERSION 宏）；install_headers
  含 erfaextra.h/erfadatextra.h；注册 t_erfa_c / t_erfa_c_extra 两个 meson
  test 目标。

## 排障优先级链检索记录（实现前）
1. build-chain-pitfalls.md：R8——源码/patches 禁止 `__OHOS__` 等平台条件宏；
   本补丁为纯 meson 文件，无任何平台宏。
2. 设备 knowledge/graph 命中（原文证据）：
   - E112.kv: "HMDFS 文件系统上，mktemp -d 创建的临时目录权限为 drwx--S--- 
     (2700 + setgid)，导致即使目录 owner 是当前用户，也无法在其中创建文件…
     chmod 也无法修改权限" → autotools config.status 必失败，rec=bypass。
   - E114.kv / E118.kv: 同根因，rec_command 均为手工 sed/patch configure 脚本，
     脆弱 → 支持选 (a)。
   - 注意：2.0.1 的 notes.md 把此坑写成 "E081"，是错误编号——E081 实为 musl
     缺 secure_getenv，与本坑无关。
3. 同源先例：archives/e/erfa/2.0.1/（meson+static 配方、AR/AS/STRIP/NM/RANLIB
   环境变量处理、eraVersion 等声明在 erfaextra.h 而非 erfa.h、测试代码需同时
   include erfa.h 与 erfaextra.h）。

## 上游测试（独立复核 tarball，不采信转述）
- `t_erfa_c.c`：main 调用 **246** 个测试组函数（`t_<func>(&status)`），断言
  调用点 **1398 vvd + 95 viv = 1493**（grep 统计调用点行首缩进匹配，不含
  定义行）。Scout 转述"247 组/1495 断言"与 tarball 实测不符，以实测为准。
- `t_erfa_c_extra.c`：**2** 个测试组（t_versions 3 检查 + t_leap_seconds
  2 检查 = 5 个显式检查）。
- 运行方式：conanfile build() 内 `Meson(self).test()`（`meson test -v`），
  在权威 CI 日志留证。

## 鸿蒙专有测试（builder 硬性要求）
test_package/test_ohos.c：断言 `__OHOS__` 工具链标识（实测 aarch64-linux-ohos
clang 定义 `__OHOS__ 1`、`__OHOS_FAMILY__ 1`）、LP64/musl 数据模型、meson
路线 PACKAGE_VERSION/SOFA_VERSION 配置传递（eraVersion()=="2.0.0"、
eraSofaVersion()=="20210512"）、静态库内嵌闰秒表链接闭包（eraDat(2024-07-01)
==37s）。共 7 项断言。

## 验证结果（权威 CI 回填）

- 首轮权威 CI（run 日志 `logs/ci_run1.log`，ohos-aarch64 profile）：**全绿**。
  L0 pass / L1 pass（upstream tests + test_package executed）/ L4 pass /
  L5 pass（lib/ 有内容）/ L2 skip（静态库无 bin/，属正常）；Pass rate
  100% (1/1)；L1e 破坏性负测试确认 test_package 真实依赖被测包。
- 上游测试（conan create 内 `meson test -v`）：**Ok: 2 / Fail: 0 / Skipped: 0**。
  - t_erfa_c OK 0.05s —— 246 组/1493 断言调用点全部通过
    （日志证据："t_erfa_c validation successful"）。
  - t_erfa_c_extra OK 0.03s —— 2 组/5 显式检查全部通过。
  - 结论：248/248 测试组 = 100% 通过；无 NOT_RUN、无 NO_UPSTREAM_TESTS。
- test_package：`test_erfa`（消费侧 4 项）与 `test_erfa_ohos`（OHOS 专有
  7 项断言，`[OHOS-OK]` ×7 + "OHOS-specific checks: all passed"）全部通过。
- CI 的 mirror-fallback 曾把 conandata.yml 的 url 原地改写为 gh-proxy 镜像
  列表（E415 型改写），CI 结束后已 `git checkout` 还原为提交态，未进候选。
- 回填本节属纯文档变更；对最终候选树以 `logs/ci_run2.log` 完整复跑权威 CI
  确认（结果见交付报告）。

