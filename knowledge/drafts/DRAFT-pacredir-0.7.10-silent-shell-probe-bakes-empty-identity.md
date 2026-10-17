# Makefile 解析期的 `$(shell)` 发行版探测静默产出空串，并把空身份编进二进制

- **Status**: DRAFT
- **出处**: pacredir 0.7.10 适配 HarmonyOS PC（本 PR）
- **上游**: <https://github.com/eworm-de/pacredir>，tag `0.7.10`，tarball sha256
  `fa73fb62dda010f20d85cfb8864ec993421641edde2cf999a91dd835c0fe36cc`
- **构建系统**: 裸 GNU Makefile（无 configure / cmake / meson）
- **严重度**: 2（构建全绿，交付物核心功能恒不生效）
- **门禁命中**: 无。这类问题**任何现有门禁都拦不住**——`conan create` rc=0、
  `-Wall -Werror` 零告警、L0-L5 全过。

## 相关既有条目（撞车判定）

写本条前已 grep `knowledge/graph/index.tsv`（768 条）与 `knowledge/doc/`、
`knowledge/drafts/`。`makepkg` 全库 0 命中，`os-release` 仅 1 条无关草稿
（DRAFT-ttyload-0.5…，讲 `/proc/stat` 读权限）。最相近的 6 条及本条增量：

另用仓内工具做了机器相似度复核（`ohc-run.py draft-review <本草稿> --top 4`）：
质量预检 signature/root_cause/rec 三项全绿，最近邻 **E067 score 0.14**、
E097 0.12、E034 0.06、E525 0.06，工具给出 **`create`（疑似新知，无高相似条目）**。
下面再按机制手工列出真正需要区分的 6 条：

| 条目 | 它覆盖什么 | 本条增量 |
|---|---|---|
| **E320**（`fmemopen` / `AC_CHECK_FUNCS`） | 符号存在但运行期语义不可用，探针给出**错误的肯定**，误置 `HAVE_FMEMOPEN=1` | 方向相反：本条是探测**静默产出空值**（错误的否定/缺失），且失败点在构建系统自己的 shell 探测，不在 libc 能力探针；产物里错的是**字符串常量**而非 `#ifdef` 分支 |
| **E302**（`open_memstream` / 空捕获输出） | CMake 符号级探测放行了一条契约已破的能力 | 同上；且 E302 的后果在**测试捕获**上可见，本条后果在运行期功能上、且默认 verbose=0 时连日志都没有 |
| **E290**（`check_symbol_exists` 检不出 typedef） | 探针机制与被探测物类型不匹配 → 错误的 `HAVE_*` | 同属「探测机制错配」家族，但 E290 会**响亮失败**（编译报 unknown type），本条 rc=0 |
| **E090**（meson `host_system == 'linux'`） | 平台身份被判成 `harmonyos`，条件分支落空 → 少编源文件 → `undefined symbol` | 同为「平台身份错」，但 E090 的身份是**非空但判错**且以链接错误收场；本条身份是**空**且以 rc=0 收场 |
| **E205**（config.guess/sub 三元组；P001 禁 `--build/--host`） | 用伪装的 gnu 三元组绕过系统检测 | 本条 `forbid_1` 直接复用它的原则：不得在构建机上伪造 `/etc/os-release`、`/etc/makepkg.conf` 去骗过探测 |
| **DRAFT-smalt-0.7.6-pre2010-config-guess-sub-ohos-triplet** | pre-2010 `config.sub` 的 `-linux*)` 兜底把 `-linux-ohos` 静默 sed 成畸形的 `-linux-gnu-ohos` 且 **rc=0** | 与本条同为「rc=0 静默产出畸形值」，但机制完全不同：smalt 是 shell 脚本白名单 + sed 改写（畸形**非空**值），本条是 make 的 `$(shell)` 只收 stdout、丢 rc（**空**值）；产物形态也不同（三元组 vs 编进二进制的身份常量）；判据不同（smalt 可直接跑 `config.sub` 复现，本条只能查产物） |

结论：无既有条目覆盖「`$(shell)` 探测静默返回空串 + 空值被编进产物」这一形态，
可独立申报。上述 5 条已填入 `.kv` 的 `similar_to`。

## Scope（何时用本条）

命中全部三条时适用：

1. 上游用 **Makefile / .mk**（不是 autoconf、不是 cmake、不是 meson）；
2. Makefile 在**解析期**用 `VAR := $(shell ...)` 探测宿主环境，且探测命令形如
   `source /etc/<发行版文件> && echo $X`、`lsb_release`、`dpkg-architecture`、
   `rpm --eval`、`uname` 派生、`git describe`（无 tag 时兜底缺失）、
   `date --utc --date=@N`（GNU date 专有）等；
3. 该变量的值最终**进入产物**（写进生成头 / `-D` 宏 / 版本字符串 / 嵌入资产）。

**不适用**：探测失败会主动报错的形态——autoconf 的 `AC_CHECK_*` 编译探针、
meson 的 `dependency()` / `host_system`、`config.guess` 的
`unable to guess system type` + `exit 1`。那些按 E001/E090/E290/E320 与
smalt 那条草稿处理。

## Symptom（真实日志）

本条的关键特征是：**没有症状**。构建全绿。

pacredir 0.7.10 的 `Makefile` 顶部：

```make
ARCH	:= $(shell shopt -u extglob && source /etc/makepkg.conf && echo $$CARCH)
ID	:= $(shell shopt -u extglob && source /etc/os-release && echo $$ID)
DATE	:= $(shell date --utc --date=@$(SOURCE_DATE_EPOCH) '+%a, %d %b %Y %H:%M:%S GMT')
export ARCH ID DATE
...
version.h: $(wildcard .git/HEAD .git/index .git/refs/tags/*) Makefile
	printf '#ifndef VERSION_H\n#define VERSION_H\n#define VERSION\t"%s"\n#define ARCH\t"%s"\n#define ID\t"%s"\n#endif\n' "$(VERSION)" "$(ARCH)" "$(ID)" > $@
```

在没有 `/etc/makepkg.conf`、`/etc/os-release` 的机器上最小复现（实测，本机 macOS；
OHOS worker 与 clean CI 容器同理，因为这些文件本来就不存在）：

```console
$ make -f Makefile.probe ; echo "make_rc=$?"
/bin/sh: /etc/makepkg.conf: No such file or directory
/bin/sh: /etc/os-release: No such file or directory
date: illegal option -- -
--- probe.h ---
#define ARCH ""
#define ID ""
#define DATE ""
--- end ---
make_rc=0
```

注意三点：

1. **`make_rc=0`** —— make 完全不知道出了问题；
2. stderr 那几行是**唯一**线索，且它们是 `/bin/sh` 与 `date` 打的、不带
   `error:` / `warning:` 前缀，任何按 `error|Error|failed` 过滤日志的门禁都抓不到；
3. 三个宏全部是空串，接着就被 `printf` 写进 `version.h`，编进二进制。

若照原样构建 pacredir（不传 `ARCH=`/`ID=`），产物里的身份串会退化成：

```text
pacredir v0.7.10  /  (built: ...)        ← ID 与 ARCH 之间只剩一个孤零零的斜杠
pacredir/0.7.10 ( / )                    ← curl User-Agent
<td>Distribution:</td><td><b></b></td>   ← 状态页两个空单元格
```

## Root Cause

GNU make 的 `$(shell ...)` 有两个语义要点，叠在一起就构成了静默失败：

- **只捕获 stdout**：子命令的 stderr 原样透传到 make 的 stderr，不进变量；
- **丢弃退出码**：`$(shell)` 的展开值就是 stdout 文本，rc 不参与任何判断
  （要拿 rc 得用 `.SHELLFLAGS` + `-e` 或 `$(info $(.SHELLSTATUS))`，上游没用）。

于是 `shopt -u extglob && source /etc/makepkg.conf && echo $$CARCH` 这条链：

```text
shopt 不是 POSIX sh 内建（/bin/sh 上即失败）
  → && 短路，source 不执行 / 或 source 因文件缺失失败
  → && 短路，echo 不执行
  → stdout 为空
  → make 拿到 ""，rc 依然是 0
```

空值随后被写进**生成头**成为编译期字符串常量。这一步是本条危害的放大器：
常量一旦编进产物，就与运行环境彻底解耦——设备上没有 `/etc/os-release`
也不再有机会补救，因为值在交叉编译时就已经定死了。

### 下游消费点决定危害等级（本例实测）

pacredir 把这个身份用在三处，危害递增：

**(a) DNS-SRV TXT 对等体过滤 —— 功能整体失效**

```c
/* pacredir.c:398-401 */
if (strncmp((char*)txt_data, "arch=" ARCH, txt_len) == 0)
        match |= DNS_SRV_TXT_MATCH_ARCH;
if (strncmp((char*)txt_data, "id=" ID, txt_len) == 0)
        match |= DNS_SRV_TXT_MATCH_ID;
...
/* pacredir.c:422-425 */
if (match < DNS_SRV_TXT_MATCH_ALL) {
        write_log(verbose, LOG_INFO, "Host %s does not match distribution and/or architecture.", canonical);
        goto finish_service;
}
```

`ARCH` 为空时 needle 退化成裸 `"arch="`（5 字符 + NUL）。真实 peer 的 TXT 是
`arch=aarch64`（`txt_len=12`），`strncmp` 比到第 5 字节：needle 是 `'\0'`、
txt_data 是 `'a'` → 不相等 → 返回非 0 → `DNS_SRV_TXT_MATCH_ARCH` **永不置位**。
`id=` 同理。于是 `match` 恒为 0，恒小于 `DNS_SRV_TXT_MATCH_ALL`（=3），
**每一个** mDNS 发现到的 peer 都走 `goto finish_service` 被丢弃。

更糟的是那行日志是 `write_log(verbose, LOG_INFO, ...)`——**verbose 级**。
默认 `verbose=0` 时连这一行都不打。最终交付物的表现是：

> 守护进程正常启动、状态页正常返回、日志一片干净，就是永远找不到 peer。

这在现场极易被误判成「局域网里没有 pacserve 镜像」或「mDNS 组播被网络设备拦了」，
排查方向会完全跑偏。

**(b) curl User-Agent** 退化成 `pacredir/0.7.10 (/)`——对端按 UA 做统计或
做兼容判断时会拿到垃圾值。

**(c) 状态页**的 Distribution / Architecture 两个单元格渲染成空——运维看不到
这个实例认为自己在什么平台上跑。

## Workaround / 修复

本次采用的方案（`archives/p/pacredir/0.7.10/conanfile.py`）：
**把权威来源从「构建宿主的发行版文件」换成「构建系统已知的目标平台定义」**，
在 make 命令行显式传入。

```python
_ARCH_LITERAL = {"armv8": "aarch64", "armv7": "armv7", "x86_64": "x86_64", "x86": "i686"}

arch  = _ARCH_LITERAL.get(str(self.settings.arch), str(self.settings.arch))
os_id = str(self.settings.os).lower()          # OHOS → "ohos"，Linux → "linux"
self.run('make -C "%s" pacredir CC="%s" CFLAGS_EXTRA="$EXTRA" '
         'VERSION="%s" ARCH="%s" ID="%s"'
         % (self.source_folder, cc, self.version, arch, os_id), env="conanbuild")
```

为什么这条能生效、且不污染别的平台：

- **命令行变量优先级最高**：GNU make 里命令行赋的变量会覆盖 Makefile 内的
  `:=` 赋值，且被覆盖变量的右值**不再展开**——那条 `$(shell source /etc/...)`
  根本不会执行，stderr 噪声也一并消失；
- **值来自任务的目标平台定义**（Conan settings），与构建宿主是什么发行版彻底解耦，
  交叉编译与原生编译得到同一结果；
- **在 Arch/glibc 上同样正确**：`ARCH=aarch64 ID=arch` 与上游探测结果一致，
  不是平台特例分支，因此补丁/配方都不含平台宏（R8 / PF5 合规）；
- **不改上游源码**，零 patch（本条与 pacredir 那个 musl 头文件补丁是两回事）。

### 验收：必须查产物，不能查日志

```console
$ strings bin/pacredir | grep -E 'pacredir v|arch=|\(ohos'
pacredir v0.7.10 ohos/aarch64          # 启动横幅 / Server 响应头
pacredir/0.7.10 (ohos/aarch64)         # curl User-Agent
arch=aarch64                           # DNS-SRV TXT 匹配串
<td>Distribution:</td><td><b>ohos</b></td>
<td>Architecture:</td><td><b>aarch64</b></td>
```

修复前这 5 行分别是 `pacredir v0.7.10 /`、`pacredir/0.7.10 (/)`、`arch=`、
`<b></b>`、`<b></b>`。本 PR 的 test_package 第 3 项与第 10 项就是把
`ohos/aarch64` 固化成断言（CLI 输出与 HTTP `Server` 响应头两个观测面各一条）。

## Prevention

1. **预扫描**：`.kv` 的 `prescan_pattern` 已给出可直接派生的规则，
   范围 `Makefile*, *.mk, GNUmakefile*`：
   ```
   \$\(shell[^)]*(/etc/(os-release|makepkg\.conf)|lsb_release|dpkg-architecture|rpm --eval)
   ```
   命中即应在适配前把「这个变量会进产物吗」问清楚。
2. **适配清单里加一步「身份常量核对」**：凡是产物带版本/平台字符串的，
   构建完 `strings` 一遍，确认没有空位、没有孤零零的分隔符。成本几秒，
   能拦住这一整类问题。
3. **别把 `$(shell)` 的 stderr 吞掉**（`2>/dev/null`、`|| true`）：那几行
   "No such file or directory" 是唯一可 grep 的线索。
4. **禁止在构建机上伪造发行版文件**（P001 / E205 同一原则）：
   `echo 'ID=arch' > /etc/os-release` 之类会把假身份编进产物，还会污染
   共享 worker 上的其他任务。

## References

- GNU make 手册 §8.15 「The shell Function」：只返回标准输出，退出码经
  `.SHELLSTATUS` 才可取，默认不参与判断
- GNU make 手册 §6.10 「Overriding Variables」：命令行变量覆盖 Makefile 赋值
- 本 PR：`archives/p/pacredir/0.7.10/conanfile.py`（`_ARCH_LITERAL`、`build()`）、
  `archives/p/pacredir/0.7.10/notes.md`（问题 #5）、
  `archives/p/pacredir/0.7.10/test_package/test_pacredir.py`（检查项 3、10）
- 上游消费点：`pacredir.c:398-401`（TXT 匹配）、`pacredir.c:422-425`（丢弃分支）、
  `pacredir.c:599`（User-Agent）、`pacredir.c:966`（`Server` 响应头）、
  `html.h`（状态页模板）
- 相关条目：E090、E205、E290、E302、E320、
  DRAFT-smalt-0.7.6-pre2010-config-guess-sub-ohos-triplet
