# DRAFT-gtk-libintl-gettext-deadlock：gtk 自建 gettext shim 导出 g_libintl_* 导致跨库绑定重入死锁

> 状态：草稿（`draft: true`）｜ `contributor_id: 232`｜`authors: chaqiuwuguang`｜查重结论已回填（见末节）
> 提交到 `knowledge/drafts/` 时，文件名改为 `DRAFT-gtk-libintl-gettext-deadlock.md`（与 `id:` 一致）。
> 证据来源：`md汇总/留痕工作/gtk/验收执行手册-V1V2V3与真编-20260920.md`、`md汇总/留痕工作/gtk/evidence-20261001/`（含 `SHA256SUMS.txt`）
> **新增价值定位（2026-10-01）**：**根因机制（跨库符号绑定劫持 + 重入 `g_once`）+ 最小复现件 + E107 边界修正**；
> 修复手段①（消费侧 `-lintl`）已由既有草稿记录，本条**不主张为新方案**。

## 现象

同一根因在两个阶段有两条可观测签名：

### ① 运行期（主缺陷）：加载 libgtk-3（3.24.38）后，首次 gettext 译文查找永久 futex 等待

最小复现探针（链接 libgtk-3 + 一次 `g_dgettext`，20 秒超时；探针为 `~/tmp/gtkgettext-probe.c`，已随证据包入库 `evidence-20261001/gtkgettext-probe.c`）：

```text
[gtkprobe] start (libgtk-3 is loaded)
[gtkprobe] after setlocale
exit=124                                ← 挂死（dirty = gtk/3.24.38）
```

同一探针在 gtk/3.24.43 下：

```text
[gtkprobe] start (libgtk-3 is loaded)
[gtkprobe] after setlocale
[gtkprobe] after glib_gettext
[gtkprobe] after g_dgettext
[gtkprobe] done
exit=0                                  ← 正常
```

故障栈取证（faultlog，前 60 行已入库 `evidence-20261001/faultlog-stack-head60.txt`）：帧 pc == `g_libintl_gettext+0x14`，落在 `libgtk-3.so` 内；寄存器 `x8=0x62`（arm64 futex）、`x1=0x80`（`FUTEX_WAIT|PRIVATE`）、`x3=0`（**无超时**）——该结论已固化在 `archives/g/gtk/3.24.38/conanfile.py:448-449` 的配方注释里。

### ② 链接期（下游暴露）：gtk 移除 shim 后，libgsf 的未定义 `g_libintl_*` 无处可解

```text
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_libintl_bindtextdomain
>>> referenced by /storage/Users/currentUser/.conan2/p/b/libgs4c22bbfd5cd47/p/lib/libgsf-1.so

ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_libintl_bind_textdomain_codeset
>>> referenced by /storage/Users/currentUser/.conan2/p/b/libgs4c22bbfd5cd47/p/lib/libgsf-1.so
```

## 根因

`g_libintl_*` 在 OHOS 生态里的**合法提供者有两类**（注意：不是"唯一一种"）：

1. glib 包内 vendored 的 `frida/proxy-libintl`，编译成共享 `libintl.so.8`（其 `libintl.h` 用宏把标准 gettext API 改写成 `g_libintl_*`）；这条改名经 glib 的 `includedirs`（`package_info()`，`archives/g/glib/2.84.0.1/conanfile.py:228-233`）→ `.pc` 的 `Cflags` → AutotoolsToolchain 的 `CPPFLAGS` 传播给所有消费者。glib 配方 `conandata.yml:6-11` 直接写明 "cmd-pkgs libintl uses g_libintl_* renames"。
2. 本仓已合入的 **`libintl/0.26.1`**（自研合并 shim，`combined_libintl.c`）：同时导出 `libintl_*` 与 `g_libintl_*` 两组符号，用于"系统 libpython 需 `libintl_*` 而 glib 只导 `g_libintl_*`、两者同进程互斥"的 GI 运行时场景（见该包 `notes.md`）。

**无论哪种提供者，第三方库都不得自行以默认可见性重复导出这些符号** —— 这正是本条的缺陷面。

问题出在 **gtk/3.24.38 配方额外自建了一个同名 gettext shim**（`_build_gettext_shim_object()`，`archives/g/gtk/3.24.38/conanfile.py:403-455`）：它定义了 7 个 `g_libintl_*` 函数（`:426-432`）并以**默认可见性**导出进 `libgtk-3.so`。而 `libglib-2.0.so` 自身的 `g_libintl_*` 是**未定义符号**，按装载顺序（libgtk-3.so 第 73 行 → libglib-2.0.so 第 86 行 → libintl.so.8 第 187 行，`/proc/<pid>/maps` 实测）被绑到 **libgtk 里的那份重复定义**；shim 再回调 glib 的 `glib_gettext`/`g_dgettext`，而此刻 glib 的 gettext 一次性初始化（`_g_dgettext_should_translate` 的 `g_once`）仍在进行、且只有一个线程 → `g_cond_wait`/futex 永久等待（timeout=NULL）→ 进程在启动初期挂死。配方注释 `:410-420` 与 `:444-450` 完整记录此机制（含"隐藏可见性让 libglib 去绑 libintl.so.8"的正确解）。

> 这是**"跨库符号绑定顺序 + 一次性初始化语义"级别**的根因：既有 `libintl`/`gettext` 条目全部描述"符号**缺失**"，本条描述"符号**重复且被优先绑定**"，方向相反。

该 shim 的默认可见导出**同时掩盖了第二个缺陷**：`libgsf/1.14.58` 的 `libgsf-1.so` 自己链了 libintl，但被 libtool 丢弃、未进 `DT_NEEDED`（`libgsf-1.la` 的 `dependency_libs` 无 libintl；`NEEDED` 仅 `libgmodule-2.0.so.0` / `libxml2.so.16` / `libc.so`），`.dynsym` 里 `g_libintl_bindtextdomain` / `g_libintl_bind_textdomain_codeset` 仍为 `U`——过去靠 gtk/3.24.38 的 shim 在链接期"顺手兜住"，换成按设计无 shim 的版本后立刻爆出（机制见 `archives/l/libgsf/1.14.58/conanfile.py:426-437` 注释）。

## 可复用修复模式

> 定位：以下 ① 为**工程首选**（但有既有知识，本条不主张为新方案）；② 为**源头修法**（本条的修复落点）；③ 为**预防门禁**（建议形态，尚未在配方实现）。

1. **① 工程首选：让引用 `g_libintl_*` 的库/程序链接共享 libintl**（不要自行再定义这些符号）。
   - 链接行追加**绝对路径 + `-Wl,--no-as-needed`**（后者保证 libintl 进 `DT_NEEDED`；OHOS 加载器即时重定位，运行时必须有符号提供者）：
     `-Wl,--no-as-needed <glib 包>/lib/libintl.so`
   - 落点示例：abiword 配方遍历生成 Makefile、把该 flag 追加进每个 `LIBS =` 行（`archives/a/abiword/3.0.8/conanfile.py:398-445`）；依据是 automake 链接命令行末尾恒为 `$(LIBS)`（实测 `src/Makefile:1025`）。
   - ⚠️ **同类做法已存在**：`DRAFT-autoreconf-bootstrap-intltool-prefix-and-gtk-lintl` 第④坑已写"glib 的 `g_libintl_*` 要单独补 `-lintl`（且不能进 configure 的 LIBS）" ⇒ 本条**不重复主张**该方案，只作为工程首选引用。
2. **② 源头修法：消除非法外泄（二选一）**
   - **升级**到不含该 shim 的 gtk/3.24.43：其 `_augment_glib_pkg_config` 给 `glib-2.0.pc` 补 `-lintl`，正确链共享 libintl（`archives/g/gtk/3.24.43/conanfile.py:271-292`）；
   - **若必须保留 3.24.38**：给 shim 编译期加 `-fvisibility=hidden`（`3.24.38/conanfile.py:444-451` 已含该 flag 及说明），使其不进入动态符号表。
   - ⚠️ **方向对照**：`DRAFT-ohos-hidden-symbol-visibility-exports-zero` 讲的是**相反**问题（上游 meson 无条件 `gnu_symbol_visibility:'hidden'` → 导出 0 个符号 → 消费者链接失败，rec 是"放开隐藏"）；本条是"**默认可见导致非法外泄**，要收紧"。两者关键词同为 `visibility hidden` 但**处置方向相反**，勿混用。
   - ⚠️ `-Wl,--exclude-libs` **无效**：只作用于**静态库成员**，而 shim 是普通 `.o`。
3. **③ 预防门禁（建议，尚未实现）：导出符号白名单断言**
   - 在配方 `test_package` / CI 增加断言：框架库只允许导出公共 API；对关键依赖做**符号存在性**断言（如 glib 的 `libintl.so.8` 应导出 9 个 `g_libintl_*`）。
   - 现状：gtk 两版 `test_package` 已内置 **gettext 死锁最小验收件**（探针），可直接扩为白名单断言，使"非法外泄 / 意外缺失"成为可回归门禁。
4. **禁止**：
   - 不要**再次自行定义并以默认可见性导出** `g_libintl_*`（重演跨库绑定死锁）；
   - 不要用**静态 `libintl.a`**（引入第二套 glib/GObject 类型系统，R60 已证实，`archives/l/libgsf/1.14.58/conanfile.py:193-201`）。

## 验证证据

- **gtk 真编**：3.24.43 在 OHOS 真机 `conan create` 通过，910/910 目标，耗时 **2 分 25 秒**，`Package '…' created`，`test_GTK` 1/1 Passed。
- **V1 导出计数**（`llvm-nm -D --defined-only <libgtk-3.so> | grep -c g_libintl_`，逐包复核见 `evidence-20261001/nm-evidence.txt`，sha256 `de8188ba40161af383157d7f37671ad6b9fe50b89af3c62cd091d3612f51fc23`）：
  - gtk/3.24.43 系（`libgtk-3.so.0.2411.32` / `libgdk-3` / `libgailutil-3`）全为 **0**；
  - gtk/3.24.38（脏包，`libgtk-3.so.0.2406.32`）为 **7**；13 个缓存包逐包复核后仅该脏包非 0。
- **V2 最小探针**：A(dirty=3.24.38)=`exit=124`（挂死）；B(3.24.43)=`[gtkprobe] done`、`exit=0`。
- **V3 端到端**（gtk/3.24.43 上的 abiword 上游测试套件 `AbiWord-test`，无 `LD_PRELOAD` shim）：`TF_Test: 152 tests, 0 failures.`、`exit=0 lines=206`、`cannot-open-display count=0`；`broadwayd` 取自自建 gtk 包并成功监听（`Listening on …/broadway6.socket`）。
  - **已跑两轮、两轮一致**：早期一轮测试树为旧树 `abiwo73f4a7cb347e7`；复跑一轮使用重编后的新树 `abiwo762bda1133789`（`round21.sh 3.24.43`）。最近一轮（10-01）在 `p/b/abiwoc92f5653b0903/b/build-release` 上复现 152/152（`r21-console-431.log`）。
- **abiword 重编**（含消费侧 libintl 注入）：`conan create` 全程 **26 分 27 秒**，`Package 'ef4df7840c87128318a0e10e9601b188' created`，`test_package 1/1 Passed`；`.libs/abiword` 的 `NEEDED` 含 **`libintl.so.8`**；`llvm-nm -D --defined-only <libintl.so> | grep g_libintl_` 列出 **9 个**定义。

> 证据包：`md汇总/留痕工作/gtk/evidence-20261001/`（31 个哈希文件 + `SHA256SUMS.txt`），含两份失败原文（`abiword-gtk431-failed1.log` / `failed2.log`）、`faultlog-stack-head60.txt`、`nm-evidence.txt`、探针与垫片源码、`round13/15/19/20/21.sh`。

## 查重结论

> 检索范围：**main 已合并知识图谱**（`knowledge/graph/index.tsv` + `knowledge/doc/` + `knowledge/drafts/`），关键词 `g_libintl` / `gettext` / `libintl` / `proxy-libintl` / `futex` / `deadlock` / `visibility`；
> **另含开放分支盲区核查**（`git ls-remote --heads` + 逐条读取）。

| 命中的相似条目 | 其根因 | 与本条的差异 |
|---|---|---|
| **E015** | `undefined symbol: libintl_dgettext`（缺 libintl） | **符号缺失 vs 重复定义**：本条是"系统里多了一份**默认可见**的同名定义"，导致跨库绑定劫持 |
| **E027** | `libintl_gettext` / `bindtextdomain` undefined（平台未预装 libintl） | 同上（缺符号） |
| **E107** ⭐ | `undefined reference to g_libintl_*`（GLib 静态库依赖 `libintl.a`）→ 该条给的方案是"**建中间共享库导出 `g_libintl_*` 供下游链接**" | **正是本条缺陷的反面做法**：以默认可见性再导出一份 `g_libintl_*`，在 OHOS 上会重演跨库绑定死锁。**E107 适用边界应修正为**：仅当"系统中**不存在**任何默认可见的同名定义、且消费者确实缺少符号提供者"时可用；**一旦已有合法提供者**（glib 交付的共享 `libintl.so.8`，或本仓的 `libintl/0.26.1` 合并库），正确做法是**链接该共享库**，**不得**再造中间共享库重复导出 |
| **E123** | meson 静态/动态库链接选错（`build.ninja` 的 `.so`→`.a`） | 链接期选库 ≠ 运行期符号劫持 |
| **E142** | `g_libintl_dgettext: symbol not found`（relocate 失败） | 缺符号 |
| `DRAFT-13410-trueprint-libintl-stub-header` | libintl 桩头文件（编译期） | 头文件桩 ≠ 运行期重复导出 |
| `DRAFT-appstream-1.2.0-ohos-gettext-proxy-libintl-header` | OHOS sysroot 的 `libintl.h` 为空 stub，无 gettext/dgettext 声明 → 复用 glib 的 proxy 头补位 | 编译期头文件缺失，非运行期符号绑定 |
| `DRAFT-appstream-1.2.0-r04-static-glib-consumer-link-ffi-intl` | **静态** glib 消费者链接缺 libffi 与 intl（glib 的 pc-fix 剥离了 `Requires.private`） | 静态链接 + `.pc` 剥离成因 ≠ 动态库重复导出劫持 |
| **`DRAFT-autoreconf-bootstrap-intltool-prefix-and-gtk-lintl`** | 无 configure 的 GTK autotools 应用引导链四坑；**第④坑**："glib 的 `g_libintl_*` 要单独补 `-lintl`（不能进 configure 的 LIBS）" | 🟡 **修复手段重叠**：本条**不主张**该手段为新方案，仅作为工程首选引用；本条的独立增量在**根因机制**（为什么必须补）+ **最小复现件** + **E107 边界修正** |
| **`DRAFT-ohos-hidden-symbol-visibility-exports-zero`** | 上游 meson 无条件 `gnu_symbol_visibility:'hidden'` 且源码无 default 标注 → 编译成功但导出 0 个符号，消费者链接必失败 | 🟡 **关键词重叠、方向相反**：该条要"放开隐藏"，本条要"收紧非法外泄"；两者互为边界，均需保留 |
| **开放分支 `docs/knowledge-libintl-dual-symbol`**（未合入） | "Python 与共享 glib 同进程 **libintl 符号冲突**"，解法＝合并 `libintl.so.8`（同导出两组符号）置 `LD_LIBRARY_PATH` 首位 | 🟡 **表象相近、根因不同**：该条是"**两套合法 provider 同进程互斥**"（无第三方库外泄）；本条是"**第三方库（libgtk）重复导出劫持 libglib 的绑定**"。该解法已落地为本仓 `libintl/0.26.1` 包；本条不与其竞争，仅声明边界 |

**结论**：**已合并知识中无同根因条目**。既有 `libintl` / `gettext` 相关条目分三类——①"符号缺失"（E015/E027/E142、appstream 两类、trueprint）；②"链接期选库/`.pc` 剥离"（E123、appstream-r04）；③"隐藏策略方向相反"（hidden-symbol-visibility-exports-zero）。本条的根因是"**符号重复导出导致跨库绑定劫持 + 重入 `g_once` 永久 futex 死锁**"，**根因相反、非重复**；并**修正 E107 的适用边界**（见上表）。

**开放分支盲区**：已核对上述 `docs/knowledge-libintl-dual-symbol`（未合入，根因不同）；提交前建议再执行 `git log --all --oneline -- knowledge/drafts | head -20` 复核一次。
