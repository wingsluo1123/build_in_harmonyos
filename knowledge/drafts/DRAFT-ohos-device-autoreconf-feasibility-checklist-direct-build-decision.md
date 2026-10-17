# DRAFT-OHOS-DEVICE-AUTORECONF-FEASIBILITY-CHECKLIST-DIRECT-BUILD-DECISION：真机 autoreconf 再生可行性三步盘点，不可满足时的确定性直编决策

> Source: rmcast 2.0.0 适配（feat/rmcast-2.0.0-codex，2026-10-13）
> 状态：DRAFT — same-stem .md/.kv pair

## 一句话

老 autotools 包（2007-2012 年代 config.guess/sub，无 aarch64）在真机上
"必须 autoreconf 再生"，但**再生是否可行要先盘点设备栈三件套**（autoconf /
automake+aclocal / libtoolize+libtool.m4）；OHOS 设备只有 autoconf 时再生是
死路（AC_PROG_LIBTOOL 无 libtool.m4 无法展开，且这不可通过 PATH 修复），
应直接切换到**确定性直编配方**，而不是反复试错。

## 使用说明（可复制流程）

### ① 上游侧判据：再生是不是硬前置

```bash
grep timestamp <archive>/config/config.guess <archive>/config/config.sub
# timestamp 早于 2012 → 不含 aarch64 → configure 无法接受 aarch64-unknown-linux-gnu
#   （表现为 "Invalid configuration ... machine not recognized" 或静默选错平台分支）
grep -E "AC_PROG_LIBTOOL|LT_INIT|AM_CONFIG_HEADER|AC_TYPE_SIGNAL|AC_FUNC_SETVBUF_REVERSED" configure.in
# 命中 → 现代工具链下 autoreconf 会因宏移除而失败，需补丁（见查重 DRAFT-13410 族做法）
```

### ② 设备侧盘点：再生栈三件套（一次 ssh 搞定）

```sh
which autoconf aclocal automake libtoolize      # autoconf 在 /data/service/hnp/bin
head -1 $(which aclocal 2>/dev/null)            # 看 shebang！
find / -name "libtool.m4" 2>/dev/null | head    # AC_PROG_LIBTOOL/LT_INIT 的硬前提
```

三件套判定表（rmcast 实测）：

| 组件 | 状态 | 后果 |
|---|---|---|
| autoconf 2.72 | ✅ hnp 自带 | autoreconf 能启动 |
| automake/aclocal | ⚠️ 脚本在 `usr/local/bin` 但 shebang 指向不存在的 perl 路径 | `Can't exec "aclocal"`；改 shebang 也不够（见下） |
| libtoolize / libtool.m4 | ❌ 完全没有 | `AC_PROG_LIBTOOL` 无定义，autoreconf 必败，**无法通过装 PATH 修复** |

判定：**任一硬缺失且短期补不了 → 放弃再生，走直编**。
（E116 的"从源码编译 automake"路线存在，但 libtool 也要从源码编，成本远超直编。）

### ③ 直编配方的确定性要点

1. **前提审计**：`grep -rn 'HAVE_CONFIG_H\|HAVE_[A-Z]' src/`。
   源码零 `HAVE_*` feature 宏、config.h 仅被 `#ifdef HAVE_CONFIG_H` 门控时
   （本例恰是），可完全绕过 configure（该门控陷阱详见 dact 草稿）。
2. **上游 CFLAGS 逐字迁移**：从 `src/Makefile.am` 的 `lib*_la_CFLAGS` /
   `AM_CFLAGS` 原样搬进配方（本例：`-DRANDOM_TIMERS -DREFRESH -DSINGLE_NACK
   -DSUPPORT_FOR_NEW_MEMBERS -D_REENTRANT -fno-strict-aliasing`），保证与
   autotools 路径产物同构。
3. **工具链变量一律从 `AutotoolsToolchain(self).vars()` 取**（注意是**方法**，
   要调用），CC/CFLAGS/AR 都不硬编码（R33）。
4. **含引号的 `-D` 宏要用 shell 单引号整体包裹**：
   `-DSTR_VERSION=\"2.0.0\"` 会被 sh 剥成裸 `2.0.0`，使
   `"RMCAST "STR_VERSION` 这类字符串拼接编译失败（`expected ')'`）；
   写成 `'-DSTR_VERSION=\"2.0.0\"'` 才能让引号到达编译器。
5. **静态库直编**：`$AR rcs librmcast.a *.o`；shared 需求时
   `clang -shared -Wl,-soname,...` 并用 **cp 物化 soname/linker 名**
   （HMDFS 不保 symlink，见相关草稿）。
6. 静态库直编会让 `--with-pic`/libtool 语义消失，`fPIC` 选项由配方自己的
   两遍编译实现。

## 适用范围

- 老 autotools 包 + OHOS 真机（或任何无完整 autotools 栈的交叉环境）；
- 源码对 config.h 的依赖限于 `HAVE_CONFIG_H` 门控（或能写出一小型 config.h）；
- Makefile.am 中能拿到完整、自洽的编译器标志。

不适用：configure 承担实质探测/代码生成（AC_CHECK_* 结果被源码真实引用、
BISON/FLEX 等生成步骤）且无法人工落定的项目。

## 输入 / 输出

- 输入：上游归档（config 目录 timestamp、configure.in 宏清单、Makefile.am）。
- 输出：三选一决策——① 原生 autoreconf；② 补丁后再 autoreconf；③ 直编配方；
  以及（③ 时）从 Makefile.am 迁移的 CFLAGS/源文件清单与 AR/CC 获取方式。

## 示例（rmcast 2.0.0 实证）

- config.guess/sub timestamp 2007-07-22 / 2007-06-28 → 无 aarch64，再生硬前置；
- configure.in 含 `AM_CONFIG_HEADER`、`AC_TYPE_SIGNAL`、
  `AC_FUNC_SETVBUF_REVERSED` 等 6 个被现代 autotools 移除的宏 → 补丁 0001；
- 设备盘点：autoconf 2.72 ✅、aclocal shebang 死链 ⚠️、libtool.m4 ❌ → 直编；
- 直编 8/8 源码 + `ar rcs` + 两工具链接，真机 conan create exit 0，
  test_package 4/4 PASS（与配置路径产物行为一致）。

## 查重

| 既有条目 | 关系 |
|---|---|
| E116（compile-automake-from-source） | 那条给"修好 automake"路线；本条给"先盘点再决定放弃再生"的判定表，并指出 libtool.m4 缺失是无解项 |
| dact-0.8.42-autoconf-direct-build-hidden-premises | 那条讲直编的两个隐蔽前提（HAVE_CONFIG_H 门控、功能表自洽）；本条讲**再生可行性盘点与直编决策**，其门控审计作为本条第 1 步被引用 |
| DRAFT-E652-parasail（autoreconf triplet pin） | 那条是能再生时 --host 三元组钉法；本条是不满足再生前提时的分支 |
| DRAFT-libvpd（bootstrap perl interpreter relocation） | 那条是修 shebang 使 bootstrap 可用；本例她bang修好后仍死于 libtool.m4 缺失，故引出直编分支 |
| DRAFT-E564-oldstyle-config-guess-ohos-reanchor | 那条是旧 config 脚本的原生构建 reanchor；互补（那条保留 autotools 路径） |

## 关键词

autoreconf, aclocal, libtool.m4, AC_PROG_LIBTOOL, config.guess timestamp,
aarch64, 直编, 直接编译, Makefile.am CFLAGS 迁移, AutotoolsToolchain vars,
-D 引号, 单引号保护, 确定性构建, OHOS 设备工具链盘点
