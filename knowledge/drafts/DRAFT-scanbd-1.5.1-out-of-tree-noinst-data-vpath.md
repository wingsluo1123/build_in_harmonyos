# DRAFT: Autotools noinst_DATA 规则用 `$@.in` 读模板，out-of-tree 构建失败

- **id**: DRAFT-scanbd-1.5.1-out-of-tree-noinst-data-vpath
- **severity**: 2
- **category**: autotools, out-of-tree, vpath, build-system, conan
- **draft**: true

## 错误签名

```
Makefile.conf.in: No such file or directory
make[1]: *** [Makefile:840: Makefile.conf] Error 1
```

## 根因

Automake 自定义规则把模板路径写成 `$@.in`（构建目录下的目标名），而模板文件真实位置是
`$(srcdir)`。Shell 的重定向/参数展开不会跟随 VPATH，因此：

- 源码树内构建（`srcdir = .`）：恰好命中，长期无人发现；
- out-of-tree 构建（Conan build folder ≠ source folder）：`Makefile.conf.in` 不在当前目录，规则失败。

scanbd 1.5.1 的实例（`Makefile.am`）：

```make
Makefile.conf: Makefile.conf.in configure
	...
	     -e 's|@PACKAGENAME@|$(PACKAGE)|g' $@.in > $@
```

## 触发条件

- 上游只用 in-tree 方式构建（tarball 发布、无 CI），VC 里看不出来；
- 配方把 build folder 与 source folder 分离（Conan 默认）。

## 修复（推荐）

补丁把规则输入与前置条件都带上 `$(srcdir)`，`Makefile.in` 与 `Makefile.am` 同步改：

```diff
-Makefile.conf: Makefile.conf.in configure
+Makefile.conf: $(srcdir)/Makefile.conf.in configure
-	     -e 's|@PACKAGENAME@|$(PACKAGE)|g' $@.in > $@
+	     -e 's|@PACKAGENAME@|$(PACKAGE)|g' $(srcdir)/$@.in > $@
```

in-tree 构建下 `$(srcdir)` 展开为 `.`，两种构建方式同时成立。

## 兜底

在源码目录内构建（`srcdir = .`）可绕过，但破坏 build/source 分离，且源码目录并发复用不可靠，
仅作最后手段。

## 禁止

1. 在构建目录手工 `cp`/`touch` 出模板 —— 丢失 `@PACKAGEVERSION@`/`@PACKAGENAME@` 替换；
2. 用 shell 改写源文件/生成文件绕过补丁登记（R6/R16）；
3. 把 out-of-tree 失败当作"平台限制"跳过 —— CI 干净构建必然复现。

## 验证

Conan build folder（≠ source folder）执行 `make`：打补丁前失败，打补丁后通过；
in-tree 构建回归正常。

## 关联

- 类似条目：E114（HMDFS mktemp 目录权限，同属"上游只在特定构建环境验证过"类）、E236（`.la` 硬编码路径）
