# infnoise 0.3.3 适配笔记

## 编译环境
- 构建系统: makefile（software/Makefile.linux 手工 Makefile；init-build 因 F068 嵌套源码误判 autotools）
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built（本地 W3 验证通过，待 PR CI）

## 源码与版本来源
- 上游官方 tag：`leetronics/infnoise` 0.3.3（19bb69894724d87b32b7b9b86022bb4b26c919f8）
- waywardgeek/infnoise 主仓仅有 4 个 OshPark prototype tags，无 0.3.3；CHANGELOG 与 software/README 均指向 leetronics 发布体系
- 官方 tarball：https://codeload.github.com/leetronics/infnoise/tar.gz/refs/tags/0.3.3
- SHA-256: b6b411051cf2eb781943038afe8f677f829ebf4cf58c341a72e0bed84e8b216f
- tarball 全量 339 文件（software/ 88 + tests/ 198 + kicad/eagle/images 等）

## 编译步骤

```bash
# 依赖（ohpcd 仓已发布）
conan download "libftdi/1.5" -r=ohpcd --only-recipe   # libs=ftdi1, requires libusb/1.0.27
conan download "libusb/1.0.27" -r=ohpcd --only-recipe

# 手工构建验证（work 目录，依赖注入）
cd software
make -f Makefile.linux CC=clang \
  FTDI_INCLUDE="-I <ftdi>/include/libftdi1 -I <usb>/include/libusb-1.0" \
  LDFLAGS="-L<ftdi>/lib -L<usb>/lib -Wl,-rpath-link,<ftdi>/lib -Wl,-rpath-link,<usb>/lib"

# tools 工具集
cd tools && make CC=clang CFLAGS="-Wall -Wextra -Werror -std=c99 -O2 -I <ftdi>/include/libftdi1"
```

产物：`infnoise`（CLI 二进制，arm64 OHOS musl）、`libinfnoise.a`、`libinfnoise.so`（含 version-script 导出
listUSBDevices/initInfnoise/deinitInfnoise/readRawData/readData）、tools 8 个工具
（passgen/healthcheck/findlongest/entcheck/hex2bin/bin2hex/flipbits/dice）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build F068 嵌套源码提升把 `software/examples/libinfnoise` 误判为源码根，work 仅剩 7 文件 | tarball 是多目录仓库，init-build 自动提升嵌套源码目录 | 按既有规则从官方 tarball 手工重建完整结构（orig/work 各 339 文件） |
| 2 | `make` 时 git 探针报 "not a git repository" | Makefile.linux 用 `$(shell git describe...)`，release tarball 无 .git | 补丁 0001：固定 GIT_VERSION/GIT_COMMIT/GIT_DATE 为 0.3.3，支持环境覆盖 |
| 3 | `-I /usr/include/libftdi1` 硬编码头文件路径 | Makefile.linux 假定系统安装 libftdi1 | 补丁 0001：改为 `$(FTDI_INCLUDE)` 注入；链接行加 `$(LDFLAGS)` |
| 4 | 链接 `-lftdi1` 找不到 | FTDI 探测回退 `-lftdi1` 但链接无 -L | 补丁 0001：infnoise 与 libinfnoise.so 链接行追加 `$(LDFLAGS)` |
| 5 | 运行期找不到 libftdi1.so.2 | 动态库不在运行时路径 | 运行时注入 LD_LIBRARY_PATH（Conan 生成运行环境） |
| 6 | bats 用例 6 断言失败 | 上游 bats 断言无 "Error: " 前缀，实际输出 `Error: Can't find...`（exit 1 正确） | 记录为上游断言缺陷，不修上游测试 |

## 源码修改

- `patches/0001-software-Makefile.linux.patch`：git 探针固定版本 + FTDI_INCLUDE/LDFLAGS 注入 + 链接行补丁

## 依赖版本

- libftdi/1.5（ohpcd 已发布，依赖 libusb/1.0.27，均从源码构建通过）
- libusb/1.0.27（ohpcd 已发布）
- 无其他第三方依赖；Keccak F-1600 参考实现随源码内置

## 上游测试台账（双口径，R51）

### 枚举范围

| 测试源 | 内容 | 独立上游用例？ | 分类理由 |
|--------|------|--------------|----------|
| software/tests/infnoise.bats | 7 个 @test | ✅ 是（7 个） | 用户测试源中的独立 @test 用例（bats 框架） |
| software/tests/test_helper/ | bats-support/bats-assert（git submodule，tarball 内为空目录） | ❌ 否 | 测试框架辅助库，非独立用例 |
| software/tools/healthcheck（TEST_HEALTHCHECK 模式） | 熵健康自检工具 | ⚠️ 部分 | 自检工具可独立运行（见下），非 bats 用例 |
| software/tools/entcheck | 熵估算工具 | ⚠️ 部分 | 独立工具可运行，非测试断言 |
| tests/runtests.sh | FIPS/ent/dieharder 统计测试（需真实硬件 + 2500MiB 数据 + pv/rngtest/ent/dieharder） | ❌ 否 | 统计测试脚本，依赖真实 USB TRNG 硬件与外部统计工具，采集需数天 |
| tests/plots/*.py | 绘图脚本 | ❌ 否 | 辅助脚本 |
| tests/samples/*.bin | 预采集样例数据 | ❌ 否 | 数据文件 |
| tests/results/ | 历史测试结果 | ❌ 否 | 数据文件 |
| software/examples/libinfnoise/*.c | 示例程序（需硬件+libinfnoise） | ❌ 否 | 示例，非测试 |
| Keccak 参考实现 | SHA-3 置换函数 | ❌ 否 | 库内部代码 |

### bats 用例逐项结果（实际运行，无真实 USB TRNG 硬件环境）

| # | 用例 | 结果 | 原因 |
|---|------|------|------|
| 1 | test --raw output for expected entropy | 未通过 | 需 `ent` 外部工具（127 not found）+ 真实 USB TRNG 硬件读取随机数据 |
| 2 | test whitened output for expected entropy | 未通过 | 同上（ent + 硬件） |
| 3 | test whitened output (multiplier=10) | 未通过 | 同上（ent + 硬件） |
| 4 | test --no-output --debug | 未通过 | 需真实硬件生成熵数据（期望 timeout 124） |
| 5 | test --list-devices | 未通过 | 需真实 FTDI FT240X 设备在线（期望列出设备） |
| 6 | test --serial with not connected serial | 未通过 | exit 1 正确；但输出带 "Error: " 前缀，与上游断言字符串不匹配（上游断言缺陷） |
| 7 | test --help | ✅ 通过 | 无硬件可验证，首行 "Usage: infnoise [options]" 匹配 |

- 发现总数：7（source_declared_total）
- 实际运行：7（configured_executable_total，bats 全部实例化执行）
- 通过：1
- 未通过/不可通过：6
  - 硬件阻塞（真实 USB TRNG 设备 + ent 外部工具）：用例 1-5（5 个）
  - 上游断言缺陷（行为正确 exit 1）：用例 6（1 个）
- 全量通过率：1/7 = 14.3%（无硬件环境）；用例 1-5 恢复条件=接入 Infinite Noise TRNG 设备并安装 ent；用例 6 恢复条件=上游断言去掉 "Error: " 前缀或测试改为 --regexp

### 无硬件可运行验证（补充实测）

- `./infnoise --help`：exit 0，输出 Usage 首行 ✅
- `./infnoise --version`：exit 0，GIT VERSION 0.3.3 ✅
- `./infnoise --list-devices`（无设备）：exit 1，`Error: Can't find Infinite Noise Multiplier.  Try running as super user?`（行为符合无设备预期）
- `./infnoise --serial 4711`（无设备）：exit 1，同上错误 ✅
- tools/healthcheck 自检模式：exit 0，输出熵估计（约 0.865 bits/bit）✅
- tools/entcheck 对 tests/samples/infnoise_whitened.bin：exit 0，正常输出熵估计进度 ✅
- hex2bin/bin2hex 往返：`printf 'deadbeef\n' | hex2bin | bin2hex` → deadbeef ✅

## 鸿蒙专项测试

见 test_package/ 与测试用例（entcheck 对样例数据的熵分析作为可无硬件运行的专项验证）。

## 验证结果

```bash
# 本地 W3 验证见 .ci-result.json；bats 结果见 reports/upstream-tests-*.log
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libinfnoise.a | 30KB | 静态库（含 Keccak/healthcheck/writeentropy） |
| libinfnoise.so | 35KB | 共享库（version-script 导出 5 个公开符号） |
| infnoise | 43KB | CLI 二进制（arm64 OHOS musl） |
| tools/* | ~10-30KB | 8 个工具二进制 |

## 注意事项

- infnoise 是硬件 TRNG 读取器：完整熵输出功能必须连接 Infinite Noise USB TRNG（FT240X）设备；
  OHOS 设备无该硬件时 CLI 熵输出路径不可用，但库编译/链接/安装/CLI 基础行为（help/version/错误处理）均可验证
- 上游 bats 测试 5/7 依赖真实硬件，属真实外部硬件阻塞；非适配缺陷
- R38：构建产出 CLI（infnoise + tools 工具），需软件级 commands.json 声明
- 补丁 0001 不包含平台宏（无 __OHOS__ 守卫），仅注入式构建参数适配
## 知识路径决定

- 知识候选台账: reports/knowledge-candidate-ledger.md（逐项四范围查重 + 七轴查重 + 关系字段 + 适用边界/反例）
- **new_draft**: E549（knowledge/drafts/E549-draft-7E16.kv + .md 配对通过）——候选 4（Makefile git 探针固定）+ 候选 5（F068 C 多目录仓库边界）已验证、可跨库复用、查重为部分覆盖且存在新增差异 → **路径 B（知识库扩展）成立**
- reuse_existing: E276（conandata filename/BadZipFile）、E392（raw makefile 三陷阱）、E485（无硬件外设 stub/如实记录）
- path_a_no_knowledge: 否（存在 B 路径证据）
- PR 前缀: 【知识库扩展】
---

**编译结束**: 2026-10-15 18:14
**最终状态**: built
