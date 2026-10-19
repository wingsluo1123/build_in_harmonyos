# DRAFT-intltool-dist-configure-hard-deps：GNOME dist configure 的 IT_PROG_INTLTOOL 硬依赖去除法（8/5/3 分层口径）

- 条目主题：intltool.m4 在 GNOME dist 期被展开进预生成 configure 后形成的硬错误全量口径（**8 处相关，本环境可达 5 处，条件不可达 3 处**）、可达点的补丁降级法 + 上游原生 `--disable-nls`、以及 po/ check 目标硬挂 `.pot` 的实败例外。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：gdl 3.40.0（案例）；泛化到 IT_PROG_INTLTOOL 时代 GNOME Archive dist 包群。
- similar_to：**E015**（写明差异：E015 是**链接期** `dgettext/libintl_dgettext` undefined symbol——源码经 libintl.h 用 gettext 而链接缺 `-lintl`，修复为 `-lintl` 或运行期 NLS；本条是**构建期工具依赖**——configure 探针 + check 期 pot 再生对 intltool/perl-XML/msgmerge 工具链的供给要求，阶段、机理、修复三维均不同，无重叠）。

## 8/5/3 全量口径（gdl-3.40.0 pristine configure 实测行号）

| 行 | as_fn_error 文本 | 补丁处理 | 本环境可达性 |
|---|---|---|---|
| :17651 | "Automake 1.5 or newer is required to use intltool" | 未补 | 不可达（`am__api_version==1.01234` 守卫） |
| :17666 | "Your intltool is too old…" | 补丁#1（TAB 缩进） | 可达 |
| :17790 | "The intltool scripts were not found…" | 补丁#2 | 可达 |
| :18095 | "GNU gettext tools not found…"（存在性） | 补丁#3 | 可达（msgmerge 缺失即中） |
| :18101 | "GNU gettext tools not found…"（版本） | 补丁#4 | 可达 |
| :18151 | "perl 5.8.1 is required for intltool" | 未补 | 不可达（perl 5.42 存在且通过） |
| :18164 | "XML::Parser perl module is required for intltool" | 补丁#5 | 可达 |
| :21249 | "po/Makefile.in.in was not created by intltoolize." | 未补 | 不可达（config.status 对 shipped po/Makefile.in.in 的 INTLTOOL_MAKEFILE 标记 grep 通过） |

注意：这 8 处均**不受 USE_NLS 门控**（IT_PROG_INTLTOOL 的 configure 探针无条件执行）——"无条件"指的是不受 NLS 开关控制，不是"8 处全部可达"。

## check 期实败例外（必须如实记载）

`po/Makefile.in.in:148`：`check: all $(GETTEXT_PACKAGE).pot` —— 该规则**不受** USE_NLS
开关控制（`:96/:99` 的 `all-@USE_NLS@`/`all-no:` 只管 all 期）。因此 `--disable-nls` 下
`make check` 仍进入 po/ 执行 .pot 再生：INTLTOOL_UPDATE 为空 → 命令行塌缩为
`--gettext-package <pkg> --pot` → bash 127 → `check-recursive Error 1`。
gdl 案例实败日志（全部实跑轮复现）：

```
conan_build_gdl_3.40.0-run3.log:1490  INTLTOOL_EXTRACT="" XGETTEXT="…" srcdir=… --gettext-package gdl-3 --pot
conan_build_gdl_3.40.0-run3.log:1491  bash: line 1: --gettext-package: command not found
conan_build_gdl_3.40.0-run3.log:1492  make[1]: *** [Makefile:113: gdl-3.pot] Error 127
conan_build_gdl_3.40.0-run3.log:1494  make: *** [Makefile:529: check-recursive] Error 1
```

该失败属 **intltool 构建卫生**（.pot 再生），不是测试用例失败；配方以
`ignore_errors=True` 按设计捕获并输出机读 marker。申报与报告措辞：**逐条说明原因**，
不得宣称"make check 空转通过"。

## 证据分级（如实）

- **configure 期 5 处可达硬错误 = 探针级**：补丁为预判性落地（无 configure 实败轮）；
  三件探针证据：设备工具清点（intltool-update/merge、msgmerge、XML::Parser 全
  MISSING）、patch diff 与 pristine 原文逐 hunk 一致、补丁后探针仍真实运行的非致命
  回显（run3 log:292 `intltool-update: command not found`）。
- **check 期 po/pot = 实败日志级**（上文）。

## 修复（rec）

前置校验：①`grep -rn "bindtextdomain\|dgettext" <lib-src>/` 计数 = 0（NLS 运行时
inert 才可去活）；②盘点 `po/Makefile.in.in` 的 check 目标是否硬挂
`$(GETTEXT_PACKAGE).pot`（硬挂则按例外口径记录）。

```python
# patches/0001：可达 5 处 as_fn_error → ':'（探针保留照常报告，:17666 前是 TAB）
configure_args += ["--disable-nls"]   # 上游原生开关：all/install 期 po/ 走空 all-no/install-data-no
self.run("make check -j1", env="conanbuild", ignore_errors=True)  # check 期 po/pot 127 = 已知例外
```

## verification_cmd（自包含，已在设备实测计数）

```sh
grep -n "as_fn_error" <dist>/configure | grep -iE "intltool|gettext|XML::Parser" | wc -l
# → 8（intltool 相关硬错误总数；注意用 XML::Parser 而非裸 XML，否则 libxml 的
#   PKG_CHECK_MODULES 错误行混入计成 9）
grep -n "as_fn_error" <dist>/configure | grep -iE "intltool|gettext|XML::Parser" \
  | grep -vE "Automake 1\.5 or newer|perl 5\.8\.1|intltoolize" | wc -l
# → 5（本环境可达点）
grep -cE "^-[[:space:]]*as_fn_error" patches/0001-*.patch
# → 5（补丁降级计数；:17666 的 as_fn_error 前是 TAB，字符类必须含 [[:space:]]）
```

## forbid

PATH 上放伪造 intltool-update/merge/extract stub（echo 假 --version）骗过探针：行为
不可控，configure 假通过后 po/ 规则在 make/check 期以不可预期方式调用 stub，失败点后移。

## 关联

E015（链接期 dgettext 符号缺失——阶段/机理/修复均不同，无重叠）；邻族：gettext 相关
E027/E107/E123/E135/E142（检索 sanity 命中面，均非 intltool 工具链专题）。principles：P010、P014。
