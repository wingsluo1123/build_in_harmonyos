# oarc-dsc

DNS-OARC DSC（DNS Statistics Collector）：DNS 流量统计采集器——按配置对 pcap 输入做多维统计，
输出 XML/JSON 数据集（`dsc`），另含 `dsc-psl-convert` 转换工具。

- 上游：<https://codeberg.org/DNS-OARC/dsc>（官方源包：<https://www.dns-oarc.net/files/dsc/dsc-2.16.1.tar.gz>）
- 许可：BSD-3-Clause
- 构建系统：**Autotools**（上游源包**含预生成 `configure`**，无需 autoreconf）
- 包类型：**命令行工具**（`bin/dsc`、`bin/dsc-psl-convert` ⇒ 有软件级 `commands.json`，R38）
- 依赖：硬依赖仅 `libpcap`；`libuv` + `libdnswire` 仅 `--enable-dnstap` 分支需要（默认构建不需要）

## 版本矩阵

| 版本 | 状态 | 适配方式 | 补丁 | 备注 |
| --- | --- | --- | --- | --- |
| 2.16.1 | built | autotools：`configure` + `make -j1` + `make install DESTDIR=stage` 后按 CLI staging 惯例搬运到 `package_folder/bin` | 2 | 上游测试 18 项 **14 PASS / 4 FAIL**（4 项为平台限制，逐项见 `2.16.1/reports/test-report.md`）；W3 `conan create` EXIT=0；含知识库拓展四件套 |

## 适配要点

- **补丁 0001** — `src/dns_message.h` 补 `#include <sys/types.h>`：OHOS sysroot 不提供 BSD 风格类型别名
  `u_char`（既有知识 **E113 / E429**，方案 A 显式补头文件）。
- **补丁 0002** — `src/ip_proto_index.c` 不再无条件调用 `getprotobynumber_r`（本平台 libc **无 `_r` 族**）：
  改为 libc 能力检测 + 非重入查询 + **内置 IANA 协议号回退表**，保证设备无 `/etc/protocols` 时仍输出真协议名
  （`udp` 而非 `p17`）。主题见 `2.16.1/knowledge-extension/`。
- **autotools 平台基线**（沿用既有先例机制）：`_patch_config_sub()` 补 `ohos` 三元组
  （纯 OS 列表与 kernel-OS 组合**两处都要补**）+ `_relax_umask()`（`umask 077 → 022`）——
  分别对应先例 `aalib/0001-config.sub-ohos.patch`、`a52dec/0002-configure-umask-022.patch`；
  `make -j1` 规避平台无法创建 FIFO（make jobserver 退化为串行）。
- **打包落位**：上游 `make install` 装到 `/usr/local/bin`，配 `AutotoolsToolchain(prefix=DEFAULT_PREFIX)`
  + `DESTDIR=stage`，再由 `package()` 用 `copy(..., keep_path=False)` 搬到 `package_folder/bin`
  （与 `ofhttp/1.5.7` CLI 惯例一致），`package_info().bindirs=["bin"]`。

## 知识库拓展

`2.16.1/knowledge-extension/` — **四件套**（检测脚本 / 处理策略文档 / README / 复现脚本）：

| 文件 | 作用 |
| --- | --- |
| `detect-netdb-reentrant-gap.sh` | 扫描源码 `_r` 族调用点，并逐个函数名核对目标 sysroot `netdb.h` 是否声明 |
| `strategy.md` | 处理策略：libc 能力检测 + 非重入查询 + 内置 IANA 回退表（补丁内不含平台宏，R8） |
| `README.md` | 触发场景、适用库范围、限制、复现脚本用法 |
| `reproduce.sh` | 干净环境 A/B 复现：关策略链接失败（`undefined symbol: getprotobynumber_r`）→ 开策略输出 `17=udp` |

配套草稿：`knowledge/drafts/oarc-dsc-2.16.1-netdb-reentrant-gap.{kv,md}`。
