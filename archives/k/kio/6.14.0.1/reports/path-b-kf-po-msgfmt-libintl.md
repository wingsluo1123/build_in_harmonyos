# kio 6.14.0 · 路径 B 知识报告

**主题**：KDE Frameworks 构建期的 po 编目步骤会调用共享前缀里的 `msgfmt`，而该工具在
OHOS 上必然加载失败（无系统 `libintl.so.8`），导致 `pofiles` 目标在源码编译之前
`FATAL_ERROR`。配方级解法是一行 `KF_SKIP_PO_PROCESSING=ON`。

**知识草稿**：`knowledge/drafts/DRAFT-5027-kio-kf-po-msgfmt-shared-prefix.{kv,md}`

**交付版本**：修复随 `kio/6.14.0.1` 交付——制品仓已有 `kio/6.14.0`，改动 `conanfile.py` 后按
R37 必须递增版本号后缀；6.14.0 保持原样，新引用用 6.14.0.1。失败现场日志来自 6.14.0 的 CI。

## 1. 失败现场

kio 的 CI 构建（PR #5027）停在 `conan-build-test` 的 `[2%]`：

```
[  2%] Generating mo...
Error loading shared library libintl.so.8: (needed by /storage/Users/currentUser/usr/local/bin/msgfmt)
Error relocating /storage/Users/currentUser/usr/local/lib/libgettextsrc-0.22.5.so: libintl_gettext: symbol not found
CMake Error at .../pkg/lib/cmake/KF6I18n/build-pofiles.cmake:24 (message):
  failed generating .../build/Release/po
make[2]: *** [.../pofiles-<md5>.dir/build.make:71] Error 1
```

日志里**没有任何 kio 源码编译错误**——失败发生在源码编译之前，与 KDE 源码的 OHOS 兼容性无关。
CI 的三条通用提示（429 限流 / 依赖未构建 / 编译不过）在此全部误报。

## 2. 根因链

1. kio 的 `CMakeLists.txt` 调用 `ki18n_install(po)`（KI18n 提供，见 `KF6I18nMacros.cmake`），
   在 `ALL` 目标中生成 `pofiles-<md5>`，由 `build-pofiles.cmake` 对每个 `.po` 执行
   `${GETTEXT_MSGFMT_EXECUTABLE}`。
2. 该变量由 PATH 中的 `msgfmt` 解析；`ohos-aarch64` profile 的 `buildenv` 把共享前缀
   `$HOME/usr/local/bin`（`DEFAULT_PREFIX`）放进了 PATH。构建机当时在那里装过 gettext 0.22.5，
   于是选中 `/storage/Users/currentUser/usr/local/bin/msgfmt`。
3. 该 `msgfmt` 按 glibc 惯例 `NEED libintl.so.8`，并依赖同前缀的
   `libgettextsrc-0.22.5.so`。**OHOS 不提供系统 libintl.so.8**：`/system/lib64` 只有名字相近
   但无关的 `libintl_ani.z.so`；全机唯一的 `libintl.so.8` 位于 Python 发行版内
   （`/data/service/hnp/python.org/python_3.12/lib/`），不在构建工具的加载搜索路径上。
4. 每个 `msgfmt` 调用非零 → `build-pofiles.cmake:24` 的
   `message(FATAL_ERROR "failed generating .../po")` → `make Error 2` → 整包失败。

## 3. 复核命令（本机实测）

```sh
# 1) 项目确实走 po 编目
grep -rn 'ki18n_install(po)' <src>/CMakeLists.txt

# 2) 该变量来自 PATH 中的 msgfmt
grep -n 'GETTEXT_MSGFMT_EXECUTABLE' <ki18n_pkg>/lib/cmake/KF6I18n/KF6I18nMacros.cmake

# 3) 共享前缀里的 msgfmt 需要什么
llvm-readelf -d $HOME/usr/local/bin/msgfmt | grep -i libintl

# 4) OHOS 的系统 libintl 状况
ls /system/lib64/libintl.so.8                       # 不存在
ls /data/service/hnp/python.org/python_3.12/lib/libintl.so.8*   # 唯一副本（Python 发行版内）
/data/service/hnp/bin/msgfmt --version              # GNU gettext-tools 0.26（原生可用）
```

## 4. 解法与取舍

**推荐（配方级，一行）**

```python
# conanfile.py generate()
tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
```

依据（在制品仓的 `ki18n/6.14.0` 二进制包内实测）：

- `lib/cmake/KF6I18n/KF6I18nMacros.cmake:78` → `option(KF_SKIP_PO_PROCESSING "Skip processing of po files" OFF)`
- 同文件 `:114` → `if (KF_SKIP_PO_PROCESSING) return()`，即 `KI18N_INSTALL()` 直接返回，
  **既不生成 `pofiles` 目标，也不调用 `msgfmt`**。

取舍：包内不含 `.mo` 翻译目录（运行时本地化缺失），库功能与 ABI 不受影响。本仓既有 KF 配方
（karchive / kauth / kbookmarks / kcolorscheme / kcompletion / kconfigwidgets / accessibility 等）
采用同一取舍与同一开关。

**回退（仅在确需翻译目录时）**：让构建用可运行的 `msgfmt`——把原生 gettext
（`/data/service/hnp/bin/msgfmt`，0.26）或 gettext 工具包的 `bin` 置于共享前缀之前。此做法绑定
worker 绝对路径、不可移植，且不消除"共享前缀里那份 glibc 假设的 gettext"根因。

## 5. 与既有知识条目的边界（防误诊）

| | E135（既有正式条目） | 本条 |
|---|---|---|
| 错误特征 | `Error loading shared library libintl\.so\.8` … | **逐字重合**（同一条日志） |
| 根因 | 动态链接器拒收**未签名** `.so` | 所需库**不在加载搜索路径**，且崩溃方是构建期工具 |
| 处方 | `ohc-run.py sign-elf` | 配方跳过 po 处理 |
| 可互换？ | 否——本案没有"待签名的 libintl.so.8"，签名治不了"路径里根本没有" | |

因此草稿声明 `similar_to: E135`，并设 `forbid_1_pattern: sign-elf.*(libintl|gettext)` 拦掉误配处方。
另与 `DRAFT-glib-2.84.0.1-gettext-libintl-ld-library-path-shadow` 同源（都因"机器装过 gettext"），
但那条是**运行期 LD_LIBRARY_PATH 遮蔽**（`g_libintl_*` 缺失），本条是**构建期工具自身加载失败**；
共同教训是不要把共享前缀的 gettext 引入构建/运行环境。

## 6. 可复用边界

任何调用 `ki18n_install(po)`（KI18n 6.x 全部版本，含 6.14.0）或 `ecm_install_po_files_as_qm`
的 KDE/KF6 项目，在同款 worker 上都会以**同样的日志、不同的包名**复现。判据是一句话：
项目的 po 编目是否被关掉，以及 PATH 里那个 `msgfmt` 能不能跑。

本仓同批未设该开关的 6.14.0 配方（kxmlgui / kservice / kconfigwidgets 等）属同类未暴露风险：
它们只是尚未被那份坏 `msgfmt` 命中。
