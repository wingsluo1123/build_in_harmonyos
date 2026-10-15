# HMDFS 大小写不敏感下上游 tarball 内“根级文件 vs 同名目录”解包失败（VERSION vs version/）

Status: DRAFT
Source: xd 5.00.03（fbb-git/Frank B. Brokken）；触发事件 PR #15428 / CI #89206（2026-10-13）
同类先例：liboggz 1.1.1（根级 `PATCHES` 文件 vs 配方导出 `patches/` 目录）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| DRAFT-liboggz-1.1.1-hmdfs-patches-collision | HMDFS 大小写不敏感导致根级 `PATCHES`（文件）与配方导出的 `patches/`（目录）冲突，方案是 `excludes=["*PATCHES"]` | 该条明确写“若根级文件是构建必需，不得直接排除”，但未给出后半个方案；本例冲突双方**都在上游 tarball 内**（文件 + 目录），且被排除的 `VERSION` 文件内容**是编译必需**，因此给出“excludes + 内联补丁还原宏”的完整闭环 |
| E416 | 官方大写元数据目录与新增小写 recipe 目录双 case 并存（L0m-5 slug 门禁） | E416 是“仓库侧新增目录与官方目录大小写并存”的合规问题，发生在配方目录命名层；本例发生在 `source()` 解包层的 tarball 成员冲突 |
| E470 | cppitertools 2.3：大小写不敏感 FS 下 Bazel `BUILD` 与构建目录 `build` 冲突 | E470 是构建系统产出的目录名与上游文件冲突；本例是上游自身的两个成员（`VERSION` 文件 / `version/` 目录）冲突，且需要把被排除文件的语义补回 |
| E193 | HMDFS 大小写不敏感致测试失败 | 触发点不同（测试期 vs 取源解包期），解决方法不可直接复用 |

检索关键词：`HMDFS`、`大小写不敏感`、`IsADirectoryError`、`excludes`、`strip_root`、`VERSION`。
结论：库内已有“大小写不敏感”家族条目，但**没有**“上游成员同名 + 文件侧为构建必需”这一组合的处理方案 → 判定为本条的增量。

## Scope（何时使用）

- 上游 tarball 内存在仅大小写不同的根级条目，且**至少一方是构建必需**；
- 目标环境为 HMDFS（HarmonyOS 设备/CI）或任何大小写不敏感文件系统（macOS APFS 默认）；
- 症状固定为 Conan `get(..., strip_root=True)` 解包期的 `IsADirectoryError: [Errno 21] Is a directory: './XXX'`。

## Symptom（真实日志，CI #89206）

```
oxd/5.00.03: Uncompressing xd_5.00.03.orig.tar.gz to .
oERROR: xd/5.00.03: Error in source() method, line 82
o       get(self, **self.conan_data["sources"][self.version], strip_root=True)
o       IsADirectoryError: [Errno 21] Is a directory: './VERSION'
oL1_RESULT=fail: conan create failed
```

判定命令（先确认是否真是大小写同名对）：

```bash
tar -tzf xd_5.00.03.orig.tar.gz | tr 'A-Z' 'a-z' | sort | uniq -d
# xd-5.00.03/version
```

## Root Cause

上游 tarball 根级同时含 `VERSION`（文件：定义 `AUTHOR`/`VERSION`/`YEARS`）与 `version/`
（目录：内含 `version.h`，被 `main.ih` 以 `#include "version/version.h"` 引用）。HMDFS 大小写
不敏感使二者成为同一路径：解包先落目录、再写同名文件 → `IsADirectoryError`，`source()` 失败，
构建无法开始。注意这不是“上游包坏了”——同一份 tarball 在大小写敏感的 Linux 上可正常解包，
所以本地 macOS（APFS 默认大小写不敏感）也一样会中招。

## Recommended Fix

1. 判定：`tar -tzf … | tr 'A-Z' 'a-z' | sort | uniq -d`。
2. `source()` 排除**文件**一侧、保留目录一侧：

```python
get(self, **self.conan_data["sources"][self.version], strip_root=True,
    excludes=["*VERSION"])   # fnmatch 命中 tarball 成员 xd-5.00.03/VERSION
```
   （`*VERSION` 不命中 `version/version.h`，也不命中根级 `VERSION.h`。）
3. 被排除文件的语义必须补回——`patches/0001-inline-version-macros-for-case-insensitive-fs.patch`：

```diff
-#include "../VERSION"
+// HMDFS（大小写不敏感）无法同时容纳根级 VERSION（文件）与 version/（目录），
+// 配方在 source() 以 excludes=["*VERSION"] 排除该文件，改由此处内联其三个宏：
+#define AUTHOR  "Frank B. Brokken (f.b.brokken@rug.nl)"
+#define VERSION "5.00.03"
+#define YEARS   "1994-2025"
```
4. `conandata.yml` 用版本键声明该补丁，`export_conandata_patches()` 随配方导出，
   `build()` 开头 `apply_conandata_patches()` 应用（本包在 68 TU 编译前生效）。

## Fallback

保留 `VERSION` 文件、解包时把目录一侧改名（`version/` → `VersionDir/`），并把唯一引用点
（`main.ih` 的 `#include "version/version.h"`）改到新名字。适用于“文件侧必需、目录侧引用点少”
的情形；引用点多时不如推荐方案。

## Forbidden Approaches

- ❌ 已知冲突仍用裸 `get(strip_root=True)`：`source()` 必失败（本地/CI 一致）。
- ❌ 只 `excludes` 不补回宏：解包能过，但编译期立即报 `AUTHOR/VERSION/YEARS` 未定义（问题被推到 build 阶段）。
- ❌ 用 `rm` 删掉目录或文件来“消除冲突”：删目录丢 `version.h`，删文件丢宏，且掩盖 FS 大小写根因。

## Verification

```bash
# 1) 复现（大小写不敏感 FS 上）
conan create archives/x/xd/5.00.03 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 修复前：source() -> IsADirectoryError: [Errno 21] Is a directory: './VERSION'
# 修复后：补丁应用 -> 68/68 TU 编译 -> link tmp/bin/xd -> 包内 bin/xd 为
#         aarch64-linux-ohos ELF（NEEDED 含 libbobcat.so.6）
$ grep -n 'define VERSION' <source_folder>/version/version.h
8:#define VERSION "5.00.03"
```

## Prevention

- 立项预检可加一条：`tar -tzf <orig.tar.gz> | tr 'A-Z' 'a-z' | sort | uniq -d` 非空即预警
  大小写冲突，提前判定是否“文件侧必需”。
- 关键词：`HMDFS`、`大小写不敏感`、`IsADirectoryError`、`excludes`。

## 适用范围 / 不适用范围

| 维度 | 内容 |
|---|---|
| 适用 | 上游 tarball 内根级（或任一层）存在仅大小写不同的条目；被排除一方为文件且其内容编译必需；HMDFS/macOS 等大小写不敏感 FS |
| 不适用 | 被排除方非构建必需（只需 `excludes`，见 DRAFT-liboggz）；冲突发生在仓库侧目录命名（见 E416）；冲突方是构建系统产物（见 E470） |
| 前置条件 | 能确认被排除文件提供的语义（宏/声明）与其唯一消费者 |
| 应转用其他知识 | 仓库目录大小写合规 → E416；构建产物目录冲突 → E470；HMDFS 硬链接/符号链接限制 → P-HMDFS-001/P-FS-001 |

## References

- 触发：PR #15428 / CI #89206（xd 5.00.03，`source()` 的 `IsADirectoryError`）
- 实现：`archives/x/xd/5.00.03/conanfile.py`（`excludes=["*VERSION"]`）、`patches/0001-inline-version-macros-for-case-insensitive-fs.patch`
- 同族条目：DRAFT-liboggz-1.1.1-hmdfs-patches-collision、E416、E470、E193
