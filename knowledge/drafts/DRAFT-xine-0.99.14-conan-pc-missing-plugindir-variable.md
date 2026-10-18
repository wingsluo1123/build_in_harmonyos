# Conan 为依赖合成的 .pc 不带上游自定义变量：`pkg-config --variable=` 返回空串且 rc=0，configure 把空值拼成绝对路径

- **草稿 ID**: DRAFT-xine-0.99.14-conan-pc-missing-plugindir-variable
- **来源**: xine-ui 0.99.14 HarmonyOS PC 适配（`misc/desktops` 报 `No rule to make target '/mime.types'`，0003-configure.patch 判空后 G2 PASS）
- **分类**: conan / pkg-config / configure / build-system
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `make: *** No rule to make target '/mime.types', needed by 'xine.desktop'. Stop.`（发生在 `make` 阶段，但根因在 `configure`）
- configure 生成的 `XINE_MIME` 值为 `/mime.types`（前导斜杠 + 空目录）
- `config.log` 里对应赋值行形如 `XINE_MIME='/mime.types'`

## 根因

xine-ui 的 `configure` 用

```sh
XINE_MIME="`$PKG_CONFIG --variable=plugindir libxine 2>/dev/null || xine-config --plugindir 2>/dev/null`"/mime.types
```

推导插件目录下的 mime 数据文件，并把它作为 `misc/desktops/xine.desktop` 规则的前置条件。

上游 xine-lib 发布的 `libxine.pc` 由 `libxine.pc.in` 生成，确实带 `plugindir`。但在 Conan 流水线里
`libxine` 这个模块名由 **`PkgConfigDeps` 依据 xine-lib 配方的 `cpp_info` 合成**，只输出标准字段
（`prefix` / `libdir` / `includedir` / `includedirs` / `libs` / `cflags`），**不携带任何上游自定义变量**。

于是 `pkg-config --variable=plugindir libxine` **输出空串且退出码为 0**。这是本条的机制核心：
pkg-config 不区分“变量不存在”与“变量值为空”，两者都是空输出 + rc=0，所以
`cmd || fallback` 形式的短路回落**永不触发**（`xine-config` 那条分支同样落空）。
空串与字面量 `/mime.types` 拼接后成为绝对路径 `/mime.types`，make 把它当作必须存在的文件目标而失败。

错误出现在 `make`、指向 `Makefile`，很容易被误判为“补丁缺失/Makefile 坏了”，实际缺陷在 configure 的取值语义。

## 最小修复方案

在软件归档范围内（`archives/x/xine/0.99.14/patches/0003-configure.patch`）：把“取值”和“拼接”拆开，显式判空，
空值时让上游 `misc/desktops/Makefile.{am,in}` 里**已有的** in-tree 守卫（`cat "$(XINE_MIME)" 2>/dev/null || cat "$(srcdir)/mime.default"`）生效：

```diff
-XINE_MIME="`$PKG_CONFIG --variable=plugindir libxine 2>/dev/null || xine-config --plugindir 2>/dev/null`"/mime.types
+xine_plugindir=`$PKG_CONFIG --variable=plugindir libxine 2>/dev/null || xine-config --plugindir 2>/dev/null`
+if test -n "$xine_plugindir"; then
+	XINE_MIME="$xine_plugindir/mime.types"
+else
+	XINE_MIME=""
+fi
```

配套（同批补丁，独立成因）：`misc/desktops/Makefile.am` 与 `Makefile.in` 里 `"$(srcdir)/mime.default"`
带字面双引号，make 连引号一起当目标名 → 去引号。`.am`/`.in` 必须成对改：OHOS 上不重跑 autoreconf，
真正生效的是 `config.status` 从 `Makefile.in` 实例化的 `Makefile`（R6：不给生成文件打补丁）。

要点：

- **不要伪造 `plugindir`**（配方里写死 `/usr/local/lib/xine-plugin` 或造一个假 `.pc`）——把依赖树的真实布局写进包元数据，
  本地通过但 CI/消费方路径不符，且违反 R49 的私有 prefix 口径。
- `.pc` 继续交给 Conan 管理，配方只保证 `PKG_CONFIG_LIBDIR` 钉在 `generators_folder`。

## 验证方法

```bash
pkg-config --variable=plugindir libxine; echo "rc=$?"      # 空行 + rc=0（陷阱所在）
grep -n "plugindir" <generators_folder>/libxine.pc          # 无匹配
grep -n "^prefix=\|^libdir=" <generators_folder>/libxine.pc # 仅标准字段
./configure … && grep -n "^XINE_MIME=" config.log            # 修复后为空
```

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机 · Conan 2.29.1 + clang 15 + `ohos-aarch64` profile | 修复前 `make` 中断于 `/mime.types`；0003+0004+0005 后 `conan create` G2 PASS，`misc/desktops` 走树内 `mime.default` |
| conan-verify 门禁 | G0-G4 PASS（`reports/conan-verify-report.md`），W3 本地 CI 模拟 PASS |
| 消费者验证 | `test_package/test.sh` 27/27；C 组直接校验该链路——`xine.desktop` 的 `MimeType=` 实测 81 项（阈值 ≥50），man/pixmaps/skins 数据齐备 |

## 禁止策略

- 禁止以 `cmd || fallback` 短路代替显式判空（变量缺失时 rc=0，回落分支不会执行）。
- 禁止在下游配方里为依赖包凭空造 `pkg_config_custom_content` 之外的假路径；若某变量确实被下游需要，
  应在**依赖配方**里用 `cpp_info.set_property("pkg_config_custom_content", "plugindir=${libdir}/xine-plugin")` 声明（本条 fallback 方案），而不是在使用方硬编码。

## 相关

- 相似条目：E553（`x11.pc` 的 `prefix=/` 与 `--host` 触发交叉模式）、E608（单值 `$(LOCALBASE)` 兜底在多依赖下失配）
- 引用原则：R6（改源文件不改生成文件）、R49（依赖注入只用 build_folder 私有 prefix）
- 归档：`archives/x/xine/0.99.14/`（补丁 0003/0004/0005，notes.md 问题 2/3）
