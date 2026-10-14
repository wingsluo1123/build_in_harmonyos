# E547: 生成式 Autotools 文件导致的跨版本补丁失效

## 错误特征

把一个针对上游版本 N 编写的可移植性补丁，重放到版本 N+1 时，补丁引擎报出
「找不到对应上下文」，整个构建中止：

```text
Apply patch (portability): 0001 Use HMDFS-compatible umask ...
WARN: patches/0001-bfd-configure.patch: hunk no.1 doesn't match source file at line 18622
WARN: patches/0001-bfd-configure.patch:   expected: b'  tmp= ac_tmp='
WARN: patches/0001-bfd-configure.patch:   actual  : b''
WARN: patches/0001-bfd-configure.patch: source file is different - b'bfd/configure'
ERROR: binutils/2.47: Error in build() method, line 274
	apply_conandata_patches(self)
ConanException: Failed to apply patch: patches/0001-bfd-configure.patch
```

关键疑点：**同一批补丁用 GNU patch 手动重放时却「全部成功」**。两者结果不一致，
说明问题不在补丁语义，而在补丁引擎的匹配策略。

## 触发条件

- 项目使用 Autotools，且**在发布归档里携带生成物**：`configure`、`Makefile.in`、
  `aclocal.m4`、`config.h.in`。
- 配方把针对旧版本的补丁原样带到新版本（升级适配的常见做法）。
- 补丁由 **严格按行号匹配**的引擎应用，例如 Conan 的
  `apply_conandata_patches()` 所用的 `patch_ng`。
- 与「补丁内容有没有过时」无关：即使目标文本一字未改，也可能失败。

## 根因分析

`configure` 这类文件由 autoconf 从 `configure.ac` **生成**，其行号取决于生成它的
autoconf 版本与宏展开结果。上游发布新版本时，`configure.ac` 的任何改动都会让
生成物的行号整体位移；而补丁的 hunk 头 `@@ -18622,26 +18622,26 @@` 记录的是
**旧版本的行号**。

- **GNU patch** 默认允许 fuzz：找不到精确行号时会就近搜索上下文，因此「成功」；
- **patch_ng** 按精确偏移定位，找不到就在该处结束匹配，且不重试 → 直接失败。

所以「GNU patch 能打上」**不能**作为「CI 能打上」的证据。二者是两个不同的匹配
契约，这正是一次真实事故：25 个补丁在 GNU patch 下报 24/25 通过，在 patch_ng 下
同一个补丁直接让构建中止。

实测对照（binutils 2.46.0 → 2.47）：

| 补丁 | 目标文件 | 2.46.0 hunk 行号 | 2.47 实际行号 | 变更文本 |
|---|---|---:|---:|---|
| 0001 | `bfd/configure` | 18622 | 18641 | 完全相同 |

行号位移 19 行，文本零改动 —— 这就是纯粹的行号漂移。

## 解决方案

### 推荐方案：按「真实 diff」重新生成补丁

不要手工改 hunk 头（容易算错，且一旦算错就是静默错位），而是让机器生成：

1. 取**干净的**新版本源码树作为基线 `orig/`；
2. 复制一份 `work/`，用 GNU patch（允许 fuzz）把该补丁打上去；
3. 对 `orig/<file>` 与 `work/<file>` 做真实 diff，用结果覆盖原补丁；
4. 用**严格模式**复验：把新补丁打到干净树上，要求零 reject。

第 4 步是关键 —— 它验证的是「严格引擎能否应用」，而不是「内容看起来对不对」。

```bash
# 逐个补丁：生成 + 严格复验
for p in patches/*.patch; do
    rm -rf /tmp/o /tmp/w; cp -a src-pristine /tmp/o; cp -a src-pristine /tmp/w
    ( cd /tmp/w && patch -p1 --forward --silent < "$p" ) || { echo "APPLY-FAIL $p"; continue; }
    find /tmp/w -name '*.orig' -delete; find /tmp/w -name '*.rej' -delete
    # 生成 orig -> work 的真实 diff，写回 $p
    diff -ruN /tmp/o /tmp/w > "$p"
    # 严格复验
    rm -rf /tmp/v; cp -a src-pristine /tmp/v
    ( cd /tmp/v && patch -p1 --forward --silent < "$p" ) \
        && echo "STRICT-OK $p" || echo "STRICT-FAIL $p"
done
```

结果：binutils 2.47 上由 24/25 变为 **25/25 严格通过、0 reject**。

### 备选方案：缩减上下文并重算 hunk 头

对超大的生成文件（`configure` 动辄数万行），若不便整份重生成，可把 hunk 缩到
「唯一变更行 + 1~2 行上下文」，再对新文件重算 `@@` 起始行。上下文越短，
越依赖内容唯一性而非偏移，抗漂移能力越强。

## 禁止做法

- **不要**用 `--fuzz=99`、忽略 patch 失败、或 `|| true` 把打补丁变成「尽力而为」：
  补丁没打上，包却照样构建成功，最终交付的是**没有该适配**的产物，而测试结果
  会被当成打了补丁的结果汇报 —— 这是最危险的一种假绿。
- **不要**把「补丁应用」写成断言后接 `|| pass`，或把补丁标记为可选：这样上游一升级，
  补丁就静默退化为空操作，评审再也分不清哪些适配真正生效。
- **不要**只依据 GNU patch 的成功结果下结论。

## 验证

```bash
# 判据一：严格引擎（patch_ng / patch --no-fuzz）能否应用
( cd pristine && patch -p1 --forward --silent < patches/0001.patch ) && echo STRICT-OK

# 判据二：hunk 头行号是否与目标文件一致
grep -n '^@@' patches/0001.patch
grep -n 'umask 077' pristine/bfd/configure   # 应落在 @@ 声明的范围内

# 判据三：补丁是否真的改变了文件
patch -p1 --dry-run < patches/0001.patch | grep -c '^patching file'
```

三条同时成立，才算「补丁在新版本上真实可用」。

## 关联条目

- 与「.addrsig」那类**编译器与汇编器文本格式边界**的问题不同：本条发生在
  **补丁引擎与生成文件**之间，属于构建系统层。
- 与「上游 API 变更导致补丁语义过时」也不同：本条的症状是**完全打不上**，
  而非打上后行为错误；后者的正确处置是改写补丁语义，本条只需重算偏移。
