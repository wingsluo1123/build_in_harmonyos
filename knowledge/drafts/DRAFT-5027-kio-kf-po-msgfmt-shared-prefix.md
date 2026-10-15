# DRAFT-5027-kio-kf-po-msgfmt-shared-prefix

KDE/KF 包在 OHOS 上编译时，`ki18n_install(po)` 生成的 po 编目目标会调用 PATH 里的
`msgfmt`。构建机的共享前缀（`DEFAULT_PREFIX=$HOME/usr/local`）里若装过一份按 glibc
假设构建的 gettext，它就是被选中的那个；而 OHOS 没有系统 `libintl.so.8`，该工具连
加载都完不成，于是 po 目标以 `FATAL_ERROR` 结束，整包构建失败——**失败点在源码编译之前，
与 KDE 源码的 OHOS 兼容性无关**。

## Identity and conclusion

| Field | Value |
|---|---|
| Status | Pending review（草稿，未提升） |
| Proposed route | Path B：KF 构建期 po 编目陷阱——共享前缀 glibc 版 msgfmt 加载失败（graph 侧新边界；drafts 侧与 `DRAFT-kf-skip-po-processing-gettext-toolchain` 互补） |
| Contributor | openharmony-pc-adaptor |
| Source PR | !15358（交付，分支 `feat/kio-6.14.0.1`），head `864f0b1f50033672b8bdaa6e560e2aa1f3ac3088`；问题发现于 !5027 的 CI 诊断（文件名中的 5027 即发现该问题的 PR） |
| Package | kio/6.14.0（KDE Frameworks） |
| Failure signature | `Error loading shared library libintl.so.8` + `failed generating .../po` |
| Fix | 配方 `generate()` 设 `tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"` |

## 证据链（实测）

| # | 事实 | 来源 |
|---|---|---|
| 1 | 失败发生在 `[2%]`，日志里没有任何 KDE 源码编译错误 | CI 日志 `conan-build-test`：`[ 2%] Generating mo...` 后紧跟 msgfmt 崩溃 |
| 2 | 崩溃方是 `/storage/Users/currentUser/usr/local/bin/msgfmt`（共享前缀），非原生 `/data/service/hnp/bin/msgfmt` | CI 日志 `Error loading shared library libintl.so.8: (needed by .../usr/local/bin/msgfmt)` |
| 3 | 该 msgfmt 是 gettext 0.22.5，NEED `libintl.so.8` 且依赖 `/usr/local/lib/libgettextsrc-0.22.5.so` | 日志内 `Error relocating .../libgettextsrc-0.22.5.so: libintl_gettext: symbol not found` |
| 4 | **OHOS 不提供系统 libintl.so.8**；全机唯一副本在 Python 发行版内 | `ls /system/lib64/libintl.so.8` 无此文件（只有无关的 `libintl_ani.z.so`）；`find` 命中 `/data/service/hnp/python.org/python_3.12/lib/libintl.so.8` |
| 5 | 原生 gettext 可用：`/data/service/hnp/bin/msgfmt`（gettext 0.26）印出版本号正常 | 本机实测 |
| 6 | ki18n/6.14.0（制品仓二进制）支持该开关 | `KF6I18nMacros.cmake:78` `option(KF_SKIP_PO_PROCESSING ... OFF)`；`:114` `if (KF_SKIP_PO_PROCESSING) return()`，即不生成 pofiles 目标 |
| 7 | 本仓既有 KF 配方普遍采用同一做法 | karchive / kauth / kbookmarks / kcolorscheme / kcompletion / kconfigwidgets / accessibility 等的 `tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"` |

## 与 E135 的边界（重要）

E135 的错误特征包含 `Error loading shared library libintl\.so\.8`，与本案日志逐字重合，
所以 engine 检索会同时命中。两者必须区分：

| | E135 | 本条目 |
|---|---|---|
| 根因 | 动态链接器拒绝**未签名**的 `.so` | **所需库不在加载搜索路径**（且失败方是构建期工具 msgfmt） |
| 处方 | `ohc-run.py sign-elf` | 配方跳过 po 处理（`KF_SKIP_PO_PROCESSING=ON`） |
| 处方为何不可互换 | 本案没有"待签名的 libintl.so.8"——它压根不在 PATH/搜索路径上 | 签名不会让 msgfmt 找到一份 glibc 体系的 libintl |

因此本条目 `similar_to: E135`，并显式禁止 `sign-elf.*(libintl|gettext)` 这一误配处方。

## 与既有 gettext 沉淀的关系

- E015 / E027：**链接期** `-lintl` 缺失（undefined symbol）——不同阶段、不同症状。
- E107 / E123 / E142 / E143 / E443：`g_libintl_*` / libintl.a / gettext 脚本——均非"po 编目"路径。
- `DRAFT-glib-2.84.0.1-gettext-libintl-ld-library-path-shadow`：同样由"机器装过 gettext"引起，
  但那是**运行期 LD_LIBRARY_PATH 遮蔽**导致 `g_libintl_*` 缺失；本案是**构建期工具自身加载失败**。
  两者共同教训：不要把共享前缀的 gettext 引入构建/运行环境。
- **库内已有同主题沉淀，本条与之互补而非重复**（更正：早期草稿曾误称"库内无任何沉淀"）：
  - `DRAFT-kf-skip-po-processing-gettext-toolchain`（why6666666，2026-09-14，源自 libkomparediff2 26.04.0）：
    覆盖**工具链完全缺失**——PATH 上没有 msgfmt → `build-pofiles.cmake:24` FATAL；处方同为
    `KF_SKIP_PO_PROCESSING=ON`，并带 54 个 conanfile.py 同模式的 L2 实证。
  - 本条覆盖**工具存在但不可用**：共享前缀里有 glibc 版 msgfmt，却因 OHOS 无系统 `libintl.so.8`
    在加载阶段即崩（`Error loading shared library libintl.so.8` + `libintl_*` 重定位失败）。
    与上条的三点差异：①失败更早（动态加载期，而非"找不到工具"）；②症状不同（找到了但跑不起来）；
    ③会误命中 E135 的 `sign-elf` 处方（见上节边界表）——这正是本条的增量价值。
  - `DRAFT-13796-qqc2-breeze-style-6.7.5-kf6-ecm-cmakedeps-bridge`、`DRAFT-poxml-kf6-doctools-docbook-dtd-and-gettextpo-probe`：
    同样含该开关，属适用面旁证，机理与本条不同。
- 规模与检索口径（2026-10-14 实测，本分支检出）：graph 侧 **542** 个 `E*.kv`（编号上界 E544，
  含 429/479 两个空洞；`knowledge/graph/` 下另有 `_template.kv`、`principles.kv` 等 4 个非条目文件，
  故目录内 `.kv` 总数为 544——早前引用的 544 即混淆了这两个口径），以 `KF_SKIP_PO_PROCESSING`
  检索 **0 命中**；drafts 侧 **3155** 个 `.kv`（早前"573 条"为错误计数）。
  `draft-review` 判定 **`create`**（graph 侧无需合并），最相似 graph 条目 E027(0.19)/E015(0.12)，
  均为链接期 `-lintl` 面、阶段不同。
- 覆盖判断（更正后）：**graph 侧新边界成立；drafts 侧不新**——本条价值在于补齐"共享前缀 glibc 版
  msgfmt 加载失败"这一独立失败模式，以及与 E135 的误诊边界；是否与上述草稿合并由知识库主编裁定。

## 建议修复（配方级，一行）

```python
# conanfile.py generate()
tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
```

代价：包内不含 `.mo` 翻译目录（运行时本地化缺失），库功能与 ABI 不受影响——与本仓
既有 KF 配方取舍一致（"translations are not required for the library to function"）。

## 复核命令

```sh
grep -rn 'ki18n_install(po)' <src>/CMakeLists.txt
grep -n 'GETTEXT_MSGFMT_EXECUTABLE' <ki18n_pkg>/lib/cmake/KF6I18n/KF6I18nMacros.cmake
llvm-readelf -d $HOME/usr/local/bin/msgfmt | grep -i libintl     # 该工具 NEED 什么
ls /system/lib64/libintl.so.8                                     # 预期：不存在
/data/service/hnp/bin/msgfmt --version                            # 预期：GNU gettext-tools 0.26
```

## 待人工确认

- 是否提升为正式条目（`graph promote`），以及最终 E 编号。
- 是否把同批未设开关的 6.14.0 KF 配方（kxmlgui/kservice/kconfigwidgets 等）一并硬化——
  它们只是尚未踩到这份坏 msgfmt，风险与 kio 同源。
