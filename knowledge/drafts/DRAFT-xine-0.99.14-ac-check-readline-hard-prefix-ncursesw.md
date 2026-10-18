# 自研 m4 探测宏的假阴性：`test -f` 只遍历硬编码前缀（不看 CPPFLAGS/PKG_CONFIG），再加一句 `-lncurses` 命名假设

- **草稿 ID**: DRAFT-xine-0.99.14-ac-check-readline-hard-prefix-ncursesw
- **来源**: xine-ui 0.99.14 HarmonyOS PC 适配（`readline/8.3` 已进图、`readline.pc` 已生成，configure 仍报 `readline.h... not found`）
- **分类**: autotools / configure / detection / pkg-config / compat
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `checking for readline.h... not found`
- `*** no readline found, xine network interface will be disabled ***`
- 后果：`xine-remote` 不构建（不报错，功能静默消失）
- 同型签名：`checking for aalib-config... no`（`AM_PATH_AALIB` 用 `*-config` 探测，aalib 已发布仍探不到）

## 根因

`m4/readline.m4` 里的 `AC_CHECK_READLINE` 是上游自研宏，不是 autoconf 标准 `AC_CHECK_LIB/AC_CHECK_HEADERS`。

**第一道门：纯文件系统探测，忽略编译环境**

```m4
for i in $with_arg \
     /usr/include: \
     /usr/local/include:-L/usr/local/lib \
     /usr/freeware/include:-L/usr/freeware/lib32 \
     /usr/pkg/include:-L/usr/pkg/lib \
     /sw/include:-L/sw/lib \
     /cw/include:-L/cw/lib \
     /net/caladium/.../include:-L.../lib \
     /boot/home/config/include:-L/boot/home/config/lib; do
  incl=`echo "$i" | sed 's/:.*//'`
  if test -f $incl/readline/readline.h ; then ...
```

判定只看这几个**字面路径下是否存在文件**，不读 `$CPPFLAGS`、不读 `$LDFLAGS`、不调 `$PKG_CONFIG`。
而 R49 要求依赖交付在 `build_folder` 私有 prefix / Conan 缓存目录里——这段探测天生看不见它。
实测（探索阶段把 `readline/8.3` 加入依赖图，generators 目录已生成
`readline.pc`，`AutotoolsDeps` 已把 `-I…/include` 塞进 `CPPFLAGS`）：

```console
$ ./configure … | grep -A1 "checking for readline.h"
checking for readline.h... not found
*** no readline found, xine network interface will be disabled ***
```

**第二道门：库命名假设**

即使命中，宏还会 `AC_CHECK_LIB([readline],[cbreak])`，若 `LIBS` 仍为空则 `AC_CHECK_LIB([ncurses],[cbreak])`，
两者皆空 → `have_readline=no`。OHOS 侧 ncurses 包实测只发布宽字符单库形态：

```console
$ find ~/.conan2/p -maxdepth 5 -name "libncurses*" | sed 's|.*/lib/||' | sort -u
libncurses++w.a
libncursesw.a
```

（Conan 的 `readline.pc` 亦写 `Requires: ncursesw`。）→ 写死 `-lncurses` 的探测在 OHOS 上必空。

**结论：探不到 ≠ 不存在。** 把这类现象记成“OHOS 不支持 readline”是错误归因。

## 处置方案（按功能是否属于交付面分级）

`xine-remote` 是可选 REPL 客户端，不属于本次核心交付面 → **不改上游 m4**，登记为“不适用入口”并附两条实测证据
（configure 行 + 库命名清单）。理由：改探测宏会改变其在 Linux 上的行为，补丁不可上游化（R8/P005），
收益却只是多一个非核心程序。

若该功能属于核心交付面，优先级从低侵入到高侵入：

1. 用宏自带的正规入口：`--with-readline=<dir>` —— 它把 `with_arg` 放在遍历列表**首位**，第一道门即通过；
2. 越过第二道命名门：显式 `LIBS=-lncursesw`，或预置 autoconf 缓存变量 `ac_cv_lib_ncurses_cbreak=yes`（需实测）；
3. 最后才补丁 m4，且必须可上游化。

以上任何一条都必须写在配方的 `configure_args`/`AutotoolsToolchain` 里（显式可复现），
不能依赖 shell 环境变量（R33）；**禁止**为了让探测命中而把依赖装进共享 `/usr/local`（R49，E524 同族根因）。

## 验证方法

```bash
grep -n "for i in\|test -f\|/usr/local/include" m4/readline.m4   # 探测机制判型
ls <generators_folder>/readline.pc                                # 依赖模块是否存在
./configure … 2>&1 | grep -A1 "checking for readline.h"
find ~/.conan2/p -maxdepth 5 -name "libncurses*" | sed 's|.*/lib/||' | sort -u
```

## 验证结果

| 项 | 实测 |
|---|---|
| 依赖可见性 | `readline/8.3` 在图中、`readline.pc` 已生成、CPPFLAGS 已注入 |
| configure 行为 | 仍 `readline.h... not found` → `HAVE_READLINE` 未定义 → `xine-remote` 不构建（非阻塞） |
| 命名假设 | OHOS 只有 `libncursesw.a`/`libncurses++w.a`，`-lncurses` 探测必空 |
| 交付影响 | 5 个补丁中不含 m4 改动；`conan create` G2 PASS、test_package 27/27 |

## 禁止策略

- 禁止把“configure 探不到”直接写成 `env_unsupported` / 依赖缺失——先用上面的判据分辨假阴性。
- 禁止为非核心可选功能重写上游 m4 或以 stub 方式伪造命中。
- 禁止向 `/usr/local` 等共享前缀安装依赖以迎合硬编码探测列表（R49）。

## 相关

- 相似条目：E608（单值 `$(LOCALBASE)` 兜底在多依赖下失配）、E553（`--host` 触发交叉模式改变探测）、E524（共享 prefix 污染）
- 配套草稿：DRAFT-xine-0.99.14-extra-programs-upstream-denominator（本条作为“不适用入口”证据登记在分母里）
- 归档：`archives/x/xine/0.99.14/`（notes.md 问题 5、reports/test-report.md §2 第 6 条）
