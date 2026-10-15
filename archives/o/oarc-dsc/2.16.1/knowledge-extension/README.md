# 知识库拓展：OHOS/musl 缺 netdb `_r` 族，且设备无 `/etc/protocols`

> 样例演示库：`archives/o/oarc-dsc/2.16.1`（本目录即其知识库拓展产物，随库适配同 PR 提交）
> 相关补丁：`../patches/0002-ip-proto-no-reentrant-lookup.patch`
> 检测脚本：`detect-netdb-reentrant-gap.sh`　复现脚本：`reproduce.sh`　处理策略：`strategy.md`

## 1. 一句话

库用 netdb 的**可重入查询**（`getprotobynumber_r` / `getservbyname_r` / `getnetbyname_r` 等
`_r` 族）做协议名、服务名解析时，OHOS 的 sysroot **根本没有该族声明**：编译期只报警告
（隐式声明），**链接期直接失败** `undefined symbol: getprotobynumber_r`。即便退回到非重入版，
鸿蒙 PC 与构建 worker 上**没有 `/etc/protocols`、`/etc/services`**，非重入版也只能返回 NULL，
名字退化为数字标签（`udp` → `p17`）——上游按名字比对的测试（`*.xml_gold`/`*.json_gold`）必然失败。

## 2. 识别条件（两条同时满足即命中）

1. **源码侧**：调用 netdb 的 `_r` 族（`getproto*_r` / `getserv*_r` / `getnet*_r`）。
   样例 dsc 在 `src/ip_proto_index.c` 的 **75 / 78 两行**分别走「两参」与「POSIX 五参」两种
   签名分支，任一分支都足以让链接失败。
2. **目标侧**：目标 libc 的 `netdb.h` 未声明该族。实测 OHOS sysroot 只声明
   `getprotobyname` / `getprotobynumber`（**无** `_r` 后缀的重入版）；musl 全线如此。

`detect-netdb-reentrant-gap.sh <源码目录> [日志文件] [sysroot]` 自动完成两步判定
（源码扫描 + sysroot 头文件探测，sysroot 通过 `OHOS_SYSROOT`/`$CC -print-sysroot` 自动发现，
**不写死任何本地路径**），命中时退出码 1。

## 3. 为什么在鸿蒙 PC 上必现

- **链接期**：`ld.lld` 对 `getprotobynumber_r` 报 `undefined symbol`——不是「行为差异」而是
  「符号不存在」，任何 `-Wl,--no-undefined` 或可执行文件链接都会失败。
  实测：dsc 未打补丁时 `make` 停在 `ip_proto_index.c` 的链接步骤。
- **运行期（即便绕过链接）**：`/etc/protocols`、`/etc/services` 在鸿蒙 PC 与本机都不存在
  （`ls: /etc/protocols: No such file or directory`）。非重入版读的就是这两个文件，
  缺失时返回 NULL，调用方的 `"p%d"` 回退把 `udp` 写成 `p17`。
- **上游测试会直接抓住它**：dsc 的上游 gold 文件里是 `<IPProto val="udp" count="8"/>`，
  名字一变，`make check` 的 `-e` 比对必然失败——这让本缺口**自带可验证的判据**，
  也是它适合作为样例演示库的原因。
- 与既有条目的方向不同：**E113 / E429** 是「sysroot 头文件缺类型定义」（编译期），
  **E537** 是「动态库缺 SONAME」（链接期），本条是「**缺符号 + 缺数据文件**」的组合，
  且修法必须同时覆盖链接与运行期，故单列。

## 4. 处理策略

见 `strategy.md`，三条递进：

- **S1（样例采用）**：libc 能力检测（`__GLIBC__`/`__APPLE__`/`__ANDROID__`/`__FreeBSD__`）
  + 非重入回退 + **内置 IANA 协议表**。补丁不含任何平台宏 → R8 / preflight PF5 合规。
- **S2**：编译期探测（仿 `wxWidgets` 的 `getservbyname_r` 签名探测、`socat` 的
  `getprotobynumber_r` 存在性探测）；只解决链接期缺口，仍需叠加内置表。
- **S3**：`env_unsupported` 标记（库确实需要可重入语义时）；**禁止** stub 静默降级。

## 5. 适用库范围与限制

**适用**：任何直接调用 netdb `_r` 族、或依赖协议名/服务名**字符串**的 C/C++ 库——
网络诊断类（dsc、dnstop、tcpdump 系插件）、服务发现类（getservbyname 用户）、
连接池/代理类（`getservbyname_r` 解析 `host:service`）。

**限制**：

1. 内置表只兜「名字」，不兜别名列表（`p_aliases`），依赖别名的调用方需自行扩展表；
2. 非重入版返回静态缓冲区 → **多线程热路径**调用方应走 S2 或自行加锁；
3. **本脚本不能替代真机验证**：sysroot 探测只说明「头文件不声明」，链接与运行期语义
   仍需一次真实构建（`reproduce.sh` 的阶段 A/B 即为此设计）。

## 6. 复现脚本

```sh
# 需要目标工具链（clang + OHOS sysroot），sysroot 可通过环境变量给定
export OHOS_SYSROOT=/path/to/sysroot        # 或让 CC -print-sysroot 自报
sh reproduce.sh <dsc 源码目录> [工作目录] [日志目录]

# 只看检测结论（不需要工具链）
sh detect-netdb-reentrant-gap.sh <dsc 源码目录>
```

- **前提**：两阶段都先打 `../patches/0001-dns_message-sys-types.patch` —— 它修的是
  `u_char` 未定义（属既有知识 E113/E429），是本库**能编译**的前提，与本拓展主题无关；
  「关策略」关的是本主题的 `0002`。
- **阶段 A（关本主题策略）**：只打 `0001` → 编译只报隐式声明告警，**链接失败**，
  日志出现 `undefined symbol: getprotobynumber_r`。
- **阶段 B（开本主题策略）**：再打 `../patches/0002-*` → 链接通过，且运行输出**真协议名**
  `17=udp`（而非退化值 `17=p17`）——本机无 `/etc/protocols`，名字完全来自内置 IANA 表。
- 退出码：0 = 复现成功且策略验证通过 | 2 = 环境不满足（缺编译器/sysroot）| 3 = 缺工具 | 4 = 验证失败。

## 7. 本轮实测证据（oarc-dsc 2.16.1）

| 项 | 结果 |
|---|---|
| 阶段 A（关本主题策略：只打 0001） | 编译 rc=0（仅隐式声明告警）、链接 rc=1：`undefined symbol: getprotobynumber_r`（日志命中 1 次） |
| 阶段 B（开本主题策略：再打 0002） | 编译 rc=0、链接 rc=0、运行 rc=0；输出含 `17=udp` 1 次、`17=p17` 0 次（`REPRO_EXIT=0`） |
| 阶段 B（打开全量构建） | `conan create` EXIT=0，55 个 `.c` 全部编过、链接通过，包产出 |
| 上游测试 | `make check` 18 项：**14 PASS / 4 FAIL**（`test9`/`test_encrypted` = dnstap 未构建；`test10`/`test13` = 平台无 passwd/group 库，`id -nu` 解析不出用户名） |
| 含本维度的比对 | IPProto 维度 gold 比对通过（`val="udp"`，非 `p17`） |
| 鸿蒙消费者测试 | `test_package/test.sh`（自造 pcap → 跑包内 `dsc` → 断言 JSON 统计）EXIT=0 |
