# 处理策略：OHOS/musl 缺 netdb `_r` 族，且设备无 `/etc/protocols`、`/etc/services`

配套检测脚本 `detect-netdb-reentrant-gap.sh`、复现脚本 `reproduce.sh`，
样例库 `archives/o/oarc-dsc/2.16.1`。策略按代价从低到高排列，命中风险后按序尝试。

---

## S1 libc 能力检测 + 非重入回退 + 内置 IANA 表（样例采用）

**思路**：补丁里**不判断"是不是鸿蒙"**，而是判断"这个 libc 有没有 `_r` 族"。
用 libc 能力宏分派，glibc/macOS/Android/FreeBSD 走上游原路，musl 系（含 OHOS）走回退路径：

```c
#if defined(__GLIBC__) || defined(__APPLE__) || defined(__ANDROID__) || defined(__FreeBSD__)
    /* 有 _r 族：保持上游可重入路径不变 */
    struct protoent result, *proto = NULL;
    if (getprotobynumber_r(proto, &result, buf, sizeof(buf), &proto) == 0 && proto)
        return proto->p_name;
#else
    /* musl / OHOS：无 _r 族声明 → 非重入查询 + 内置 IANA 表兜底 */
    {
        struct protoent *pe = getprotobynumber(proto);   /* 有 /etc/protocols 时才有效 */
        if (pe && pe->p_name) return pe->p_name;
        const char *n = iana_proto_name(proto);          /* 无 /etc/protocols 时的唯一出路 */
        if (n) return n;
    }
#endif
```

**为什么不能只回退到非重入版**：`getprotobynumber()` 读的是 `/etc/protocols`。
实测鸿蒙 PC 与构建 worker 上 **`/etc/protocols` 与 `/etc/services` 都不存在**
（`ls: /etc/protocols: No such file or directory`），非重入版只会返回 NULL，
调用方若以 `"p%d"` 回退，输出就从 `udp` 退化成 `p17` —— 上游按名字比对的测试
（`*.xml_gold` / `*.json_gold` 里的 `val="udp"`）必然失败。**内置表不是锦上添花，是唯一出路。**

**为什么不用 `#ifdef __OHOS__`**：这是 libc 能力差异的可移植性修复，在任意 musl 平台
（Alpine、OpenWrt、静态构建）同样成立；框架 R8 与 preflight PF5 会拦截补丁新增行里的
平台宏，能力宏是唯一合规写法。

**必须同时检查到的编辑点**（样例 dsc 1 处函数、2 个调用分支）：

| # | 位置 | 说明 |
|---|---|---|
| 1 | `src/ip_proto_index.c:75` | `getprotobynumber_r(proto, &result)` 两参签名分支 |
| 2 | `src/ip_proto_index.c:78` | `getprotobynumber_r(proto, &result, buf, sizeof(buf), &proto)` POSIX 五参分支 |
| 3 | 回退返回值 | 上游 else 分支回退 `"p%d"`，必须替换为内置表查询，否则 gold 比对失败 |
| 4 | 内置表 | 至少覆盖会被比对的协议；建议给全 IANA 常用项（见下表） |

**要点 / 坑**：

- **两处调用点都要改**：上游为兼容老 Linux 写了两种签名分支，只改一处仍会在另一分支链接失败。
- **非重入版返回静态缓冲区**：多线程调用方需自行加锁。dsc 的统计路径是单线程聚合，
  实测无影响；若你的库在多线程热路径调用，优先考虑 S2（探测）而非本策略。
- **内置表只兜"名字"，不兜"其它字段"**：`getprotobynumber()` 还提供别名列表（`p_aliases`，
  如 `tcp` 的 `TCP`），回退路径下这些别名为空。仅当调用方依赖别名时才需要扩展。
- 内置表内容（IANA 常用项，样例补丁内置了 0–17 与常用高层协议）：

| num | name | num | name | num | name |
|---|---|---|---|---|---|
| 0 | ip | 6 | tcp | 17 | udp |
| 1 | icmp | 8 | egp | 41 | ipv6 |
| 2 | igmp | 9 | igp | 47 | gre |
| 3 | ggp | 12 | pup | 50 | esp |
| 4 | ipencap | 16 | tcp-encap | 51 | ah |
| 5 | st |  |  | 58 | ipv6-icmp |

- 验证三件事：①`git apply --check` 干净应用；②全量 `make` 链接通过（无 `undefined symbol`）；
  ③含该维度的上游测试通过（dsc：IPProto 维度 gold 比对 `val="udp"` 通过）。

**样例补丁**：`../patches/0002-ip-proto-no-reentrant-lookup.patch`（50 行，含能力分派 +
内置表 + 两处调用点改写）。

---

## S2 编译期探测（仿既有先例，适用于上游愿意接受探测的库）

**思路**：用构建系统的探测能力在 configure 期决定调用哪个 API，运行代码只有一条路径。

**仓库内已有先例**（可直接参考写法）：

- `archives/w/wxWidgets/3.3.3.1/patches/0001-probe-getservbyname-r-signature.patch`
  —— 探测 `getservbyname_r` 的**签名形态**（glibc 五参 vs 老 Solaris 六参）。
- `archives/s/socat/*/patches/*configure*.patch` —— socat 自带的 `getprotobynumber_r()`
  **是否存在**的 `AC_CHECK_FUNCS` 探测（覆盖 Linux/Solaris/AIX 变体）。

**做法**：在 `configure.ac` 加 `AC_CHECK_FUNCS([getprotobynumber_r getservbyname_r ...])`，
源码里 `#ifdef HAVE_GETPROTOBYNUMBER_R` 分派。

**代价**：需要上游源码里存在 `configure.ac` 且 CI 侧具备 autoconf/automake（OHOS 侧
automake 常缺失，需 `tool_requires` 或改 `configure` 生成物——回归到补丁形态，不优于 S1）。
另外**探测只解决链接期缺口，不解决 `/etc/protocols` 缺失**，仍要叠加内置表。

**结论**：本类缺口优先 S1；S2 仅当上游已有探测骨架、改动量更小时采用。

---

## S3 `env_unsupported` 标记 / 最小 stub（无法在配方内规避时）

**适用**：库确实需要可重入语义（多线程热路径），且内置表不可接受（例如需要完整
`/etc/protocols` 语义、别名列表）。

**做法**：

1. 在 `validate()` 中按环境抛 `ConanInvalidConfiguration`，`notes.md` / `reports/test-report.md`
   附 `reproduce.sh` 阶段 A 的日志作为可执行证据，结果按 `env_unsupported` 上报（R47/协议 §4.5）。
2. 或以 stub 兜住（返回 NULL / `"unknown"`）——**仅当上游测试不比对协议名时才可用**；
   若上游 gold 依赖名字，stub 会让测试失败，属于「把错误藏起来」，禁止。

**禁止**：伪造/篡改产物、dummy 包顶替、静默降级（忽略链接报错把没构建成功的东西标成 published）。

---

## 与既有知识的关系

| 条目 | 关系 |
|---|---|
| E113 / E429 | 同为「OHOS sysroot 头文件能力缺口」（BSD 类型别名、musl 语义差异），但触发面不同：那两条是**编译期缺类型**，本条是**链接期缺符号 + 运行期缺数据文件** |
| `alpine-baselayout` 包 | 提供 `/etc/protocols`、`/etc/services`；装上后非重入版可用，但**CI 干净环境与设备默认都没有**，不可作为配方的隐含前提 |
| `socat` / `wxWidgets` 探测补丁 | 只解决「链接期缺符号」，不解决「无 /etc/protocols 时名字退化」——本条补上该空档 |
