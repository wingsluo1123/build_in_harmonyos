# oarc-dsc 2.16.1 适配笔记

## 编译环境
- 构建系统: autotools（上游源包**含预生成 `configure`**，无需 autoreconf）
- 编译日期: 2026-10-11
- 编译器: clang（OHOS `/data/service/hnp/bin/clang`，目标三元组 `aarch64-unknown-linux-ohos`）+ GNU Make 4.4.1
- 状态: built

## 编译步骤

1. 取官方源包 `https://www.dns-oarc.net/files/dsc/dsc-2.16.1.tar.gz`
   （sha256 `2085bb9f3302c4663307c6264c77a186897636a707e32649830be85140f36779`）。
2. 打两个补丁：`0001-dns_message-sys-types.patch`（`u_char`）、
   `0002-ip-proto-no-reentrant-lookup.patch`（netdb `_r` 族）。
3. `configure` —— 交叉工具链由 `AutotoolsToolchain(prefix=DEFAULT_PREFIX)` 注入；
   配方内先 `_patch_config_sub()`（补 `ohos` 三元组）、`_relax_umask()`（`umask 077 → 022`）。
4. `make -j1` —— 平台无法创建 FIFO，make jobserver 必然退化，直接串行（避免无意义告警）。
5. `make check` —— 上游 18 项数据驱动测试真跑（结果见下）。
6. `make install DESTDIR=stage` → `package()` 按 CLI staging 惯例把二进制搬进 `package_folder/bin`
   （上游安装到 `/usr/local/bin`，`copy(..., keep_path=False)` 落位，`package_info().bindirs=["bin"]`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报 `unknown type name 'u_char'` | OHOS sysroot 不提供 BSD 风格类型别名（既有知识 **E113/E429**） | 补丁 `0001` 显式 `#include <sys/types.h>` |
| 2 | 链接报 `undefined symbol: getprotobynumber_r` | 平台 libc **无 netdb 可重入族**（`netdb.h` 只声明非 `_r` 版） | 补丁 `0002`：libc 能力检测 + 非重入查询 + 内置 IANA 协议号回退表；设备另无 `/etc/protocols`，故必须有内置表，否则维度退化为 `p17` |
| 3 | `configure` 失败，`config.guess` 不认识 `HarmonyOS` | `uname -s` = `HarmonyOS`，源包内 2022 版 `config.guess` 无该分支 | 配方 `_patch_config_sub()` 补 `ohos`（纯 OS 列表与 kernel-OS 组合**两处都要补**）→ `aarch64-unknown-linux-ohos`；先例 `aalib/0001-config.sub-ohos.patch` |
| 4 | `config.guess` 报 `can't create …/dummy.c: Permission denied` | `configure` 内 `umask 077` 建出的临时目录组无 x 位，本进程非该目录 uid 属主 | 配方 `_relax_umask()`：`umask 077 → 022`；先例 `a52dec/0002-configure-umask-022.patch` |
| 5 | make 告警无法创建 FIFO | 平台 `mkfifo` 全平台 EPERM（既定基线） | `make -j1` 串行，非致命 |
| 6 | 上游测试 4 项失败 | ①dnstap 属可选特性、本次未启用 ②平台无 passwd/group 库 | 如实申报、不阻断打包；详见 `reports/test-report.md` |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-dns_message-sys-types.patch` | `src/dns_message.h` 补 `#include <sys/types.h>`——OHOS sysroot 不提供 `u_char` 等 BSD 风格类型别名（既有知识 E113/E429） |
| `0002-ip-proto-no-reentrant-lookup.patch` | `src/ip_proto_index.c`：不再无条件调用 `getprotobynumber_r`（本平台 libc 无 `_r` 族）。改为 libc 能力检测 + 非重入查询 + 内置 IANA 协议号回退表，保证无 `/etc/protocols` 时仍输出真协议名（详见 `knowledge-extension/strategy.md`） |

## 依赖版本

- `libpcap/1.10.6` —— 唯一硬依赖；已静态吸收进 `dsc`（包内二进制 `NEEDED` 仅 `libc.so`）。
- 未启用 `--enable-dnstap` ⇒ **不需要** `libuv` / `libdnswire`（`configure.ac` 中这两个依赖在
  `--enable-dnstap` 分支内）。

## 验证结果

### 上游测试（R51 三步法：清点 → 实跑 → 如实回填）

| 项 | 内容 |
| --- | --- |
| ①清点位置 | `src/test/`；`src/test/Makefile.am` 的 `TESTS` 注册 **18** 项（全部为 `test*.sh` 数据驱动脚本，`*.conf` + 预录制 pcap + `*_gold` 期望输出） |
| dnstap 变体 | 是 —— `TESTS += test5.sh`（仅 `--enable-dnstap` 时），故开启后为 **19** 项 |
| 是否需要 root | 否（脚本用 `ln -s` 建 `.dist` 链接） |
| ②实跑命令 | `make check`（在配方 `_run_upstream_tests()` 内执行，照跑照记、不阻断打包） |
| ②实测结果 | **`UPSTREAM_DSC_TESTS total=18 pass=14 fail=4`** |
| 失败项归因 | `test9` / `test_encrypted`：dnstap 未启用（上游可选特性）；`test10` / `test13`：平台无 passwd/group 库，`id -nu` 解析不出用户名 |
| ③回填 | 本表 + `reports/test-report.md` 的对比表（无占位符） |

### 鸿蒙侧消费者用例（新增）

```bash
# W3 本地 CI 模拟：conan create（干净源码 → 构建 → make check → 打包 → test_package）
# 实测 EXIT=0
#   Package '…' created
#   test_package: PASS: oarc-dsc 包内 dsc 端到端消费者用例通过
#   产出 …/1458044657.dscdata.json（JSON 含 qtype / transport_vs_qtype 数据集，A 查询计数 ≥ 1）
```

### 知识库拓展双验证（干净环境、新建临时工作目录）

```bash
bash knowledge-extension/reproduce.sh
# 阶段 A（关本主题策略：只打 0001）：编译 rc=0（仅隐式声明告警）、链接 rc=1
#   → ld.lld: error: undefined symbol: getprotobynumber_r
# 阶段 B（开本主题策略：再打 0002）：编译/链接/运行 rc=0
#   → 输出 17=udp（退化值 17=p17 出现 0 次）
# REPRO_EXIT=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/dsc` | 796K | 主程序（ELF 64-bit LSB arm64 动态，NEEDED 仅 `libc.so`——libpcap 已静态吸收） |
| `bin/dsc-psl-convert` | — | 上游附带转换工具 |
| `etc/dsc/dsc.conf.sample` | — | 配置样例 |
| `share/man/man1`、`man5` | — | 手册页 |
| `licenses/LICENSE` | — | BSD-3-Clause |
| `knowledge-extension/` | — | 知识库拓展四件套（`detect-netdb-reentrant-gap.sh` / `strategy.md` / `README.md` / `reproduce.sh`） |

## 注意事项

- 上游默认构建硬依赖**只有 libpcap**；`libuv` + `libdnswire` 仅 `--enable-dnstap` 分支需要
  （故 `test9`/`test_encrypted` 失败＝dnstap 未构建，非适配缺陷）。
- `test10`/`test13` 失败＝平台无 passwd/group 库，`id -nu` 解析不出用户名，属平台限制，不阻断打包。
- `reproduce.sh` 的「关策略」阶段必须先打 `0001`（`u_char`，既有知识 E113），
  再关本主题的 `0002`——否则阶段 A 会先死在 `u_char` 上，看不到 netdb 缺口。
- **R6 偏离说明（W4 独立审计记 P2，已知并接受）**：`_patch_config_sub()` 与 `_relax_umask()`
  在构建期以字符串替换改写 `configure` / `config.sub` / `config.status` 这些生成文件，而非
  `patches/*.patch` 形态。理由：①上游源包**预生成** `configure`/`config.sub`（无需 autoreconf），
  补丁打在生成文件上同样属「改生成文件」，价值等同；②仓库既有同类 CLI 配方
  `archives/o/ofhttp/1.5.7`（已合并）采用同样的 in-recipe 实现，本包与之对齐以保证同类包行为一致；
  ③改为补丁形态需重生成补丁并重跑整轮 W3（`.ci-result.json` 随之失效），收益仅为形式统一。
  故按审计建议在此显式记录偏离理由。

---

**编译结束**: 2026-10-11 15:43
**最终状态**: built
