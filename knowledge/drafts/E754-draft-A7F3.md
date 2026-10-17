# 上游构建脚本硬编码 /tmp 字面量：设置 TMPDIR 无效，须补丁改为 `${TMPDIR:-/tmp}`

> Draft: `E754-draft-A7F3`（uqm 0.8.0 适配实测）

## 错误特征

configure/配置阶段出现只读文件系统报错，脚本却不打印退出原因，最终表现为
某个库"找不到"：

```
build/unix/build.sh: can't create /tmp/build.55857.tmp.c: Read-only file system
Little-endian machine detected.
Simple DirectMedia Layer version 2.x found.
build/unix/build.sh: can't create /tmp/build.55857.tmp.c: Read-only file system
build/unix/build.sh: cat: /tmp/build.55857.tmp.c: No such file or directory
libpng not found.
```

关键是**报错里的路径是 `/tmp` 字面量**，而不是 `$TMPDIR/...`。这意味着
"OHOS /tmp 只读"这条已知结论（E002）在这里**不能靠 export TMPDIR 解决**。

## 触发条件

- 构建系统: 自研脚本（`build.sh` / `Makeproject` / `build/unix/*`），非 autotools/cmake/meson
- 阶段: configuration（配置期编译探针）
- 平台: OHOS（/tmp 只读挂载，E002）

## 根因分析

脚本自身把临时文件路径写死（uqm 0.8.0 `build/unix/config_functions:19`）：

```sh
TEMPFILE="/tmp/build.$$.tmp"
```

`TMPDIR` 是"约定"，不是"机制"：只有脚本主动写成 `${TMPDIR:-/tmp}` 时才生效。
外部 `export TMPDIR=...` 对字面量赋值完全无效——脚本内联赋值会把它覆盖掉。
于是每个编译探针（`try_compile_c` / `try_pkgconfig_lib`）都在写只读 /tmp 时失败，
探测函数把"写不进临时文件"当成"库不存在"，最终以 `libpng not found.` +
异常退出收场，根因被伪装成依赖缺失。

## 解决方案

### 推荐方案

1. 先确认临时目录是"约定"还是"字面量"：

   ```bash
   grep -nE 'TEMPFILE|TMPFILE|/tmp/' build/ */build.sh 2>/dev/null
   ```

   命中 `"/tmp/..."` 即字面量 → 必须打补丁。

2. 打最小可移植性补丁（uqm 实测 1 行）：

   ```diff
   -TEMPFILE="/tmp/build.$$.tmp"
   +TEMPFILE="${TMPDIR:-/tmp}/build.$$.tmp"
   ```

   `${TMPDIR:-/tmp}` 在未设置 TMPDIR 的平台上回退原路径，不改变上游行为，
   属纯 POSIX 写法（不含 `__OHOS__` 平台宏，符合 R8）。

3. 配方内把 TMPDIR 指到隔离的可写目录，避免依赖宿主环境：

   ```python
   tmp_dir = os.path.join(self.build_folder, "tmp")
   os.makedirs(tmp_dir, exist_ok=True)
   env.define("TMPDIR", tmp_dir)
   ```

4. 用 `refresh-patch --auto` 固化为 `patches/NNNN-*.patch`。
   ⚠️ 工具盲点：`refresh_patch.EXCLUDE_DIRS` 含 `build`，脚本位于
   `build/unix/` 时规则模式会漏掉该改动；用 `ohc-run.py track-edit add`
   走编辑追踪器的精准模式（无需排除规则）才能生成。

### 禁止做法

- ❌ 只 `export TMPDIR=$HOME/tmp` 就宣称修复——脚本内联赋值优先，失败必然复现
- ❌ 把 /tmp 改成另一个硬编码绝对路径（如 /data/local/tmp），换机器即失效

## 验证

```bash
# 补丁应用后 configure 不再有 /tmp 写入报错，且原本"找不到"的库被识别
TMPDIR=$PWD/tmp ./build.sh uqm reprocess_config 2>&1 | grep -E 'libpng found|Read-only'
# 期望：libpng found.  且无 Read-only file system
```

## 关联条目

- 相关: E002（/tmp 只读）、E052（config.status tmpdir）
- 取证: uqm 0.8.0 `archives/u/uqm/0.8.0/patches/0001-build-unix-config_functions.patch`
