# 经典 Autotools tgetent 库搜索链不识别 -lncursesw（OHOS ncurses 仅交付宽字符静态库）

Status: DRAFT
Source: xaric 0.13.9（archives/x/xaric/0.13.9）
PR: 【知识库扩展】feat(xaric): 0.13.9 适配 HarmonyOS PC（待提交）

## 相关既有条目

撞库检索（2026-10-14）：

```bash
python3 scripts/ohc-run.py engine "tgetent ncursesw termcap curses configure detection"
grep -Ei "tgetent|termcap|termlib|curses|tinfo|AC_CHECK_LIB" knowledge/graph/index.tsv
grep -RliE "tgetent|termcap|tinfo" knowledge/doc/ knowledge/drafts/
```

| 条目 | 已覆盖内容 | 本条增量 |
|---|---|---|
| cdcd-0.6.6-legacy-autotools-ohos-detection-mismatches（draft） | conan ncurses 只交付 `libncursesw` 而无 `libcurses` 的根因；**单层** `AC_CHECK_LIB(curses, tputs)` → `AC_CHECK_LIB(ncursesw, tputs)` 的直接替换；configure 与 configure.ac 同改 | 其案例是单层检测，可直接把 `curses` 改名 `ncursesw`。本条针对的是 **4 层嵌套 AC_CHECK_LIB 搜索链**（termcap/termlib/curses/xtermcap）：不能改名（会破坏链顺序与语义），必须在链中**插入**一层；额外给出 configure.ac 嵌套宏括号计数、生成 configure 的嵌套 if/fi 闭合（4→5 个 fi）、bash 3.2 `sh -n` 漏报、`ac_cv_lib_*` 强分支验证方法 |
| DRAFT-12002-cmake-findcurses-no-include-dir-crossbuild（draft） | CMake `FindCurses` 交叉编译无 sysroot 概念、找不到 include 目录 | 构建系统不同（CMake vs Autotools），失败阶段不同（find 路径 vs AC_CHECK_LIB 链接 conftest）；修复手段不通用 |
| E033（正式） | musl 下 ncurses 宽字符 API（cchar_t/setcchar）需 `_XOPEN_SOURCE_EXTENDED` 宏暴露 | 编译期头文件 API 暴露问题；本条是 configure 库检测阶段的库名失配，无宏可救 |
| E524（正式） | Autotools 依赖注入共享 SYS_PREFIX 污染与逐项 REQUIRED 依赖缺失 | 依赖注入路径与环境问题；本条是纯检测链库名清单缺陷，与 prefix 注入无关 |
| DRAFT-14410-static-ncurses-beep-duplicate-symbol（draft） | 静态链接 libncursesw.a 后程序自带 beep 与库内符号重复 | 链接阶段符号冲突；本条是 configure 阶段硬失败，发生在编译之前 |

结论：根因大类（上游假设的旧库名与 conan 交付面失配）与 cdcd 草稿同族，但「嵌套检测链的插入式修复 + fi 闭合坑」未被任何既有条目覆盖，故新建草稿，`.kv` 已填 `similar_to`。

## Scope

- 适用于 configure.ac 中以**嵌套 AC_CHECK_LIB 链**逐项探测 termcap 兼容库的 Autotools 工程，典型形态：

```m4
AC_CHECK_LIB(termcap, tgetent, [LIBS="-ltermcap $olibs"],
  [AC_CHECK_LIB(termlib, tgetent, ...,
    [AC_CHECK_LIB(curses, tgetent, ...,
      [AC_CHECK_LIB(xtermcap, tgetent, ...,
        [AC_MSG_ERROR([i can not find tgetent ...])])])])])
```

- 探测函数为 `tgetent`（也可能是 `tputs`/`tgetstr`），库名清单为 termcap/termlib/curses/tinfo/xtermcap 之一或多个，**不含 ncursesw**。
- OHOS 制品仓 `ncurses/6.6`（`--enable-widec` 静态包）交付物为 `libncursesw.a`（含 `formw/menuw/panelw/ncursesw`），termcap/tinfo 接口（tgetent/tgetnum/tgetstr/tgoto/tputs）均已并入其中，**无独立 libtermcap/libtinfo/libcurses**。
- 高风险软件面：ircII 家族终端 IRC 客户端（xaric 等）、1990–2000 年代的 TUI/终端工具。
- 不适用于：CMake/meson 项目（检测机制不同）、直接 `-lncursesw` 无检测链的项目、自带 termcap 实现的项目。

## Symptom

在 OHOS 依赖面下（ncurses 仅提供 libncursesw.a）运行 configure：

```text
checking for tgetent in -ltermcap... no
checking for tgetent in -ltermlib... no
checking for tgetent in -lcurses... no
checking for tgetent in -lxtermcap... no
configure: error: i can not find tgetent.  you need to help me
```

configure 退出码非 0，`config.status`/`Makefile`/`config.h` 均不生成。

在 macOS 上用 4 个缓存变量强制前四个库均为 no 可无损复现同一检测路径（本地无 libncursesw 时最终同样 error；放入含 tgetent 的 stub `libncursesw.a` 并加 `-L` 后，新增探测点输出 `checking for tgetent in -lncursesw... yes`）。

## Root Cause

1. 嵌套 AC_CHECK_LIB 链是 1990 年代 termcap/tinfo 独立成库时代的定型写法，库名清单（termcap → termlib → curses → xtermcap）里没有 `-lncursesw`。
2. 现代宽字符 ncurses（以及 conan 仓的 ncurses/6.6）把 termcap 兼容函数并入 `libncursesw.a`，旧清单上的四个库名在 OHOS 上全部不存在 → 四个 conftest 链接测试全 no → 走到最内层 `AC_MSG_ERROR`。
3. 与单层检测的关键区别：嵌套链的每个 `action-if-not-found` 参数就是下一层 `AC_CHECK_LIB`，生成的 configure 是一棵 if/else 嵌套树。在链中**插入**一个新库探测会同时增加：
   - configure.ac：最内层 `AC_MSG_ERROR(...)` 之后一个闭合括号（链上 N 个库 → 末尾 N 个 `)`）；
   - 生成的 configure：失败分支 `as_fn_error "i can not find tgetent..."` 之后一个闭合 `fi`（末尾连续 `fi` 序列数量必须等于链上库数，4→5）。

## Recommended Fix / Workaround

以 portability 补丁（`0001-tgetent-ncursesw.patch`）同时改 `configure.ac` 与 tarball 内生成的 `configure`（conan 消费 release tarball，构建期不跑 autoreconf，只改 configure.ac 无效）。

**configure.ac**：在 `-lcurses` 与 `-lxtermcap` 两层之间插入一层，并补一个闭合括号：

```m4
        AC_CHECK_LIB(curses, tgetent, [LIBS="-lcurses $olibs"],
          [AC_CHECK_LIB(ncursesw, tgetent, [LIBS="-lncursesw $olibs"],
            [AC_CHECK_LIB(xtermcap, tgetent, [LIBS="-lxtermcap $olibs"],
              [AC_MSG_ERROR([i can not find tgetent.  you need to help me])]))])
```

**configure（生成文件）**：在 `-lcurses` 失败分支后、`-lxtermcap` 的 checking 块前，插入完整的 `-lncursesw` 检测块（`{ checking }` + `if ${ac_cv_lib_ncursesw_tgetent+:} ...` 缓存判断 + conftest 编译链接 + `{ result }` + `if test "x$ac_cv_lib_ncursesw_tgetent" = xyes; then LIBS="-lncursesw $olibs"; else`），并在 `as_fn_error ... "i can not find tgetent..."` 之后的连续 `fi` 序列中补一个 `fi`（4 个变 5 个）。

**conanfile.py generate()**：用 `self.dependencies["ncurses"].package_folder` 注入 `CFLAGS/CXXFLAGS=-I<ncurses>/include`、`LDFLAGS=-L<ncurses>/lib`（R49），使新增 conftest 能链接到 libncursesw.a。

**验证（四级）**：

```bash
patch -p1 < patches/0001-tgetent-ncursesw.patch
bash -n configure && sh -n configure     # 解析期双验证（见下）
# 强走链上前四库为 no，确认顺序 termcap→termlib→curses→ncursesw→xtermcap
./configure ac_cv_lib_termcap_tgetent=no ac_cv_lib_termlib_tgetent=no \
            ac_cv_lib_curses_tgetent=no ac_cv_lib_xtermcap_tgetent=no \
            LDFLAGS="-L<ncurses>/lib"
# 期望：checking for tgetent in -lncursesw... yes，Makefile 生成，make 成功
```

**fi 闭合坑（本条最容易踩的点）**：漏补闭合 `fi` 时，macOS 自带 bash 3.2 的 `sh -n`（POSIX 模式）可能**通过**，但 configure 实际执行到生成 `config.status` 阶段才报 `exit 258`（256+2）且无 Makefile；`bash -n configure` 则会在解析期直接报 `syntax error: unexpected end of file`。因此必须 `bash -n` 与 `sh -n` 双过。排查方法：构造最小插入块二分定位，末尾 `fi` 计数应等于链上库数。

## Fallback

CI 排障可用缓存变量绕过检测点，但必须在 notes 中记录为技术债务，且需同时保证实际链接的是 ncursesw：

```bash
./configure ac_cv_lib_termcap_tgetent=yes LIBS="-lncursesw" \
            LDFLAGS="-L<ncurses>/lib"
```

注意：缓存变量只能命中链上**真实存在**的库名语义。把不存在的库名伪报为 yes（如 `ac_cv_lib_curses_tgetent=yes`）会使 `LIBS` 被置为 `-lcurses`，链接阶段失败。

## Forbidden Approaches

1. **只改 configure.ac，不改 tarball 内 configure**：conan 不跑 autoreconf，改动不生效，CI 依旧报 "i can not find tgetent"（P003：生成文件修改必须固化为 .patch）。
2. **在依赖目录伪造 `libtermcap.a`/`libcurses.a` 软链指向 libncursesw.a**：库名假象，越过包边界、违反 R26 静态链接规范，换机器/换包 revision 即失效。
3. **只往 LDFLAGS 加 `-lncursesw`，不修检测链**：configure 在 AC_CHECK_LIB 失败处直接 AC_MSG_ERROR 退出，LDFLAGS 无机会生效。
4. **用 `ac_cv_lib_curses_tgetent=yes` 欺骗检测**：LIBS 被置为不存在的 `-lcurses`，把 configure 硬失败转成更难定位的链接失败。

## Verification

- 补丁语法：`bash -n configure && sh -n configure`（均 rc=0）
- 检测块在位：`grep -c "tgetent in -lncursesw" configure`（≥2：checking 行与缓存逻辑）
- 失败路径：4 个 `ac_cv_lib_*_tgetent=no` + 无 libncursesw 时按序输出 5 项检查后报 tgetent error（证明链完整、顺序正确）
- 成功路径：提供 libncursesw.a（stub 或 conan ncurses 包）后输出 `checking for tgetent in -lncursesw... yes`，Makefile 生成，`make` 链接成功，`LIBS` 含 `-lncursesw`
- 运行时（PTY 必需，xaric main() 先 isatty(0)，无 TTY 打印 "Woops I need a tty!" 退出）：`script -q /dev/null xaric -v` 输出 `Xaric 0.13.9`

## Prevention

- 预扫描：configure.ac/configure.in 中 `AC_CHECK_LIB((termcap|termlib|curses|xtermcap|tinfo)\s*,\s*tgetent` 且无 ncursesw 探测即高危（`.kv` 已写 prescan_pattern）。
- 适配任何 ircII 家族/老式 TUI 软件前，先 `nm <ncurses>/lib/libncursesw.a | grep -w tgetent` 确认符号归属，并在 W0 依赖预检记录 ncurses 包的实际库名清单。
- 凡改生成的 configure，提交前一律 `bash -n` 与 `sh -n` 双验证，并用 `ac_cv_lib_*` 缓存变量逐分支实跑。

## References

- xaric 0.13.9 适配：`archives/x/xaric/0.13.9/`（conanfile.py、patches/0001-tgetent-ncursesw.patch、notes.md）
- ncurses 包配方：`archives/n/ncurses/6.6/conanfile.py`（cpp_info.libs: formw/menuw/panelw/ncursesw）
- 同族草稿：`knowledge/drafts/cdcd-0.6.6-legacy-autotools-ohos-detection-mismatches.kv`（单层检测直接替换）
- 上游：https://xaric.org/ ；Autoconf AC_CHECK_LIB 嵌套 action-if-not-found 语义
