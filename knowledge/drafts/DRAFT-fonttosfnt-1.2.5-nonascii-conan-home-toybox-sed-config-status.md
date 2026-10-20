# DRAFT-fonttosfnt-1.2.5-nonascii-conan-home-toybox-sed-config-status — 非 ASCII 路径撞 toybox sed

> Status: **Draft**（待主编 promote） | severity: `2` | category: `ohos, toybox, autotools, conan, environment, portability` | Updated: 2026-10-18
> 源文件：`knowledge/drafts/DRAFT-fonttosfnt-1.2.5-nonascii-conan-home-toybox-sed-config-status.kv`
> 来源：fonttosfnt 1.2.5 适配（`feat/fonttosfnt-1.2.5`，PR #16664）

---

**关键词**：CONAN_HOME, 非 ASCII, 中文路径, 多字节, toybox sed, config.status, subs.awk, ac_delim, 分隔符自检, unterminated string, autoconf 2.72, A/B 对照

## 现象（error_signature）

`conan create` 在 **configure 末段**必挂，且报错看起来与源码毫无关系：

```text
configure: creating ./config.status
configure: error: could not make ./config.status
```

放过第一关后还有第二关：

```text
gawk: ./confXXXXXX/subs.awk:6: S["FONTTOSFNT_LIBS!-L/.../home-\M-d\M-8\M-;...: unterminated string
config.status: error: could not create Makefile
```

失败形状是**本地红、CI 绿**（CI worker 的路径形态是 ASCII），所以极易被误判成
"上游源码在 OHOS 上有问题"或"配方写坏了"。

## 根因

**入口是"构建机自带 `sed` 是 toybox 而非 GNU sed"，触发条件是"路径里有非 ASCII
字节"，两者叠加才炸。** 单看任一条都不会失败。

autoconf 2.72 生成 `config.status` 要过两道与 `sed` 相关的关：

### ① 分隔符自检（delimiter self-check）不收敛

它选一个分隔串 `$ac_delim` 并自查该串在 `conf$$subs.awk` 里出现的次数：

```sh
ac_delim_n=`sed -n "s/.*$ac_delim\$/X/p" conf$$subs.awk | grep -c X`
```

实测本包 `ac_delim` 长 **2184 字符**：

| 计数方式 | 结果 |
|---|---|
| toybox `sed -n "s/.*$ac_delim\$/X/p"` + `grep -c X` | **125** 行 |
| POSIX `awk 'index($0, d)'` 计数（= `ac_delim_num`，真值） | **127** 行 |

**少的 2 行恰好是两个「值里含中文路径」的变量** ⇒ 计数对不上 ⇒ 自检 6 轮换分隔串
都不收敛 ⇒ `could not make ./config.status`。

### ② 替换值分行时的 sed 切分把多字节值切坏

就算放过自检，`config.status` 内部那段 148 字节的行长 `sed` 也会把含多字节的替换值
切坏，生成的 `subs.awk` 引号失配：

```text
gawk: ./confXXXXXX/subs.awk:6: S["FONTTOSFNT_LIBS!-L/.../home-\M-d\M-8\M-;\M-g\M-^P\M-^F7-...: unterminated string
```

随后 `config.status: error: could not create Makefile`。
（`\M-d\M-8\M-;` = `主` 的 UTF-8 字节，`\M-g\M-^P\M-^F` = `理`；`config.status` 里三处
引号失配的行，正是三个值里带中文路径的 `FONTTOSFNT_LIBS` / `FONTTOSFNT_CFLAGS` /
`PKG_CONFIG_PATH`。）

### 两条排除性证据（避免误判方向）

- **`LC_ALL=C` 复跑同样失败** ⇒ 不是 locale / 排序问题；
- 先按"toybox sed 对长正则失配"写过一个 `sed` → `awk` 的 `configure` 补丁，
  换成 ASCII 路径后**把该补丁撤掉复跑仍然通过**（`CONTROL CONFIGURE RC=0`）
  ⇒ 根因不是"某个正则太复杂"，而是**多字节字节序列**。

## 处方（rec_approach）

`use-pure-ascii-conan-home-and-build-root-path`

**把构建路径换成纯 ASCII，不要为它改上游源码、也不要装 GNU sed。**

```sh
export CONAN_HOME="$HOME/tmp/ch/home-zhuli7-<pkg>"   # 纯 ASCII
export TMPDIR="$HOME/tmp"                             # 一并保持 ASCII

# A/B 判定（唯一变量 = 路径）
CONAN_HOME=~/tmp/ch/home-主理7-<pkg> conan create …   # ❌ could not make ./config.status
CONAN_HOME=~/tmp/ch/home-zhuli7-<pkg> conan create …  # ✅ config.status: creating Makefile / man/Makefile / config.h
```

三条纪律：

1. **先做 A/B 对照**（唯一变量＝路径），再谈源码或补丁；
2. **保持零上游补丁**：本包最终交付的补丁里**不含**任何 `sed` → `awk` 改写
   （撤掉后 ASCII 路径下仍通过，留下它就是无谓的上游偏离）；
3. **不要拿 locale 当处方**：`LC_ALL=C` 复跑同样失败。

## 边界（applicability / counterexamples）

**适用**：自带 toybox `sed`（非 GNU sed）的目标 + 构建路径 / `CONAN_HOME` 含非 ASCII
字节 + 用 autoconf 生成的 `configure` 配置的包；典型症状是 autoconf 2.72 的
`config.status` 分隔符自检不收敛。

**不适用 / 反例**：

- 路径全 ASCII（CI worker 即如此）→ **不复现**，本地红 / CI 绿；
- 路径含非 ASCII 但目标有 GNU sed → **不复现**（属 E010 的定义域）;
- `config.status` 报 **Permission denied**（临时目录不可写）→ E011 / E114 / E670 / E777 家族；
- conftest 链接 conan 共享库导致 **`cannot run C compiled programs`** → E739 / E467。

**代价**：换 ASCII 路径只是**绕开**，不是修好 toybox 的多字节处理能力；任何"必须把
非 ASCII 字节塞进 autoconf 替换值"的需求仍会失败。

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| **E010**（toybox sed/expr 对 POSIX 复杂脚本支持不完整） | 都是"toybox sed 不好用" | **E010 是 toybox 缺 POSIX 特性**——脚本里用了 toybox 不支持的构造，处方是**安装 GNU sed 替换 toybox**；**本条是多字节行处理不正确**——脚本本身完全合法，处方是**把路径改成 ASCII**。同一大主题下**两条不同机制、两个不同处方** |
| **E2095**（同名工具是 toybox 简化版时，用工包注入 GNU 版必须 `prepend_path`） | 都涉及用 GNU 版替换 toybox 版 | E2095 是**PATH 语义**（append 会被 `/bin` 遮蔽），只在本条的**回退方案**里被引用；本条主处方不改工具链 |
| **E670**（autoconf 的 `config.status` 在 HMDFS 上"刚建的目录写不进去"） | 症状同为 `config.status` 失败、同样本地红 / CI 绿 | E670 根因是**权限**（`Permission denied`），处方是把 `TMPDIR` 钉到非 HMDFS 可写根并 `chmod` 临时目录；本条根因是**多字节行被切坏**，无权限报错。两者可同时存在于一个包上，须分别坐实 |
| **E777**（`config.status` 临时目录 Permission denied，toybox mktemp 环境下用 `umask 002`） | 同属 config.status 失败家族 | E777 是 umask/mktemp 权限，处方是放宽 umask；与本条的多字节切坏无关 |
| **E739**（`AutotoolsDeps` 把依赖闭包写进 `LIBS`，致 conftest 链接 conan 共享库 ⇒ `cannot run C compiled programs`，处方＝依赖 libdir 前置 `LD_LIBRARY_PATH`） | 都在 autotools 配置期、都容易被误判成工具链问题 | **不是一回事**：E739 失败在**更早的 conftest 运行**（`checking whether the C compiler works...`），本条失败在**更晚的 `config.status` 生成**；首错原文、失败阶段与处方均不同 |
| **E467**（同一失败的**诊断侧**：先读 `config.log` 里 conftest 的完整链接命令与第一条加载错误，再判是签名/别名/路径问题） | 都是"配置期失败先读日志"的方法论 | E467 针对的是 conftest 可加载性诊断；本条的诊断对象是 `conf$$subs.awk` 的计数与 `subs.awk` 的引号失配，须用 `sed` vs `awk` 计数对照 + A/B 路径对照 |

`dedup_notes` 记录的图谱实测命中数：`ac_delim` = 0、`unterminated string` = 0、
`could not make` = 0、`could not create Makefile` = 0、`分隔符自检` = 0、
`non-ASCII path` = 0、`ASCII 路径` = 0、`路径含中文` = 0、`multibyte` = 0
（**本条机制图谱无先例**）；`subs.awk` = 1（E670）；`多字节` = 2（E727/E733，均无关）；
`toybox` = 64；`CONAN_HOME` = 18；`config.status` = 75。

## 验证

A/B 对照（同一源码、同一配方、同一 `ci/conan/profiles/ohos-aarch64`，唯一变量是 HOME 路径）：

| CONAN_HOME | 结果 |
|---|---|
| `home-主理7-fonttosfnt`（含中文） | ❌ `configure: error: could not make ./config.status`；`LC_ALL=C` 复跑同样失败 |
| `home-zhuli7-fonttosfnt`（纯 ASCII） | ✅ 一次通过：`config.status: creating Makefile / man/Makefile / config.h` → `executing depfiles commands` |

量化读数：`ac_delim` 长 2184 字符时，toybox `sed` 计数 125 行 vs POSIX `awk index()` 127 行
（真值 `ac_delim_num`）。

## 来源

- 上游任务：`archives/f/fonttosfnt/1.2.5`（PR #16664）
- 落地方式：**环境选择**（换纯 ASCII CONAN_HOME），**未改一行源码、未加补丁**；
  `patches/` 仅 `0001-config.guess.patch` 与 `0002-configure.patch`（umask 077→022），
  与本条无关
- 关键首错原文：`configure: error: could not make ./config.status`、
  `gawk: ./confXXXXXX/subs.awk:6: ... unterminated string`、
  `config.status: error: could not create Makefile`

---

*本条目为草稿。正式化请用 `ohc-run.py graph promote` 提升到 `knowledge/graph/`。*
