# DRAFT: autotools 古董库 OHOS 交叉编译四连修（CFLAGS 覆写/XML::Parser/DocBook 联网/ngettext 回退宏）

- 条目主题：2010s 桌面应用型 autotools 库（无 AC_CONFIG_HEADERS、无测试套件、doc 目录入构建图）适配 HarmonyOS PC 的组合修法。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：!15470（feat/imagination-3.6）

## 适用场景
上游停更多年的 autotools 桌面应用（GTK+ 系常见）交叉编译到 OHOS aarch64，CI 或本地 conan create 报以下任一形态：

- 交叉编译期报大量 `unknown target` / 工具链 flag 不识别（CFLAGS 被覆写）
- `checking for XML::Parser... configure: error: XML::Parser perl module is required for intltool`
- doc/ 构建阶段 `Failed to resolve docbook.sourceforge.net`（CI 沙箱无外网）
- `warning: implicit declaration of function 'ngettext'` → `error: incompatible pointer to integer conversion returning 'const gchar *' from a function returning 'int'`（-Wint-conversion）

## 诊断步骤
1. 读 configure.ac/configure.in 找 `CFLAGS=` 覆写行（区别于 `CFLAGS="$CFLAGS ..."` 追加式）。
2. 确认 intltool 使用面：只需 desktop 文件合并（纯文本）还是完整 XML 翻译链（后者真需要 XML::Parser）。
3. 查 Makefile.am 的 SUBDIRS 是否含 doc/ 及其构建是否拉网（DocBook XSL）。
4. grep 源码 ngettext 调用点；确认 configure.ac 是否有 AC_CONFIG_HEADERS（无则 ENABLE_NLS 永不定义，走非 NLS 回退宏块，检查块内宏清单完整性）。

## 修法组合
| 问题 | 修法 | patch 类型 |
|---|---|---|
| CFLAGS 覆写 | 改 `$CFLAGS` 追加式 | portability |
| XML::Parser 探测 | configure.ac 跳过（纯文本 intltool-merge 不依赖） | portability |
| DocBook 联网 | SUBDIRS 剔除 doc/ | portability |
| ngettext 回退宏缺失 | support.h 回退块补 ngettext 宏 | portability |

## 为什么不修 configure.ac 加 AC_CONFIG_HEADERS
加 config.h 头文件需同步所有 #ifdef HAVE_CONFIG_H 引用点，对停更代码库侵入面大；补单个缺失宏是最小修。

## 验证
见 .kv 的 verify_builds：conan create RC=0 + 消费者测试 93 断言全过。
