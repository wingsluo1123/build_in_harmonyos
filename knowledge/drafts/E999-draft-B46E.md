# 库内硬编码 /tmp 的 mkdtemp 在 erofs /tmp 失败——源码补丁优先 TMPDIR

## 问题
HarmonyOS `/tmp` 为 erofs 只读挂载。库源码若把运行时临时文件/目录硬编码为
`/tmp`（未读取 `TMPDIR`），则 `mkdtemp("/tmp/XXXXXX")` 直接失败，相关公开 API
报错。实例：matio `src/mat.c` 的 `Mat_mktemp()` 使用 `MAT_MKTEMP_DIR "/tmp/"`，
触发 `Mat_VarDelete()` 时报 `Cannot create a unique file name`（exit 21）。

## 根因
1. 库代码硬编码 `/tmp`，不读 `getenv("TMPDIR")` —— E002 的 set-env-var 方案对该库内部临时文件生成无效（E002 针对 configure/make 脚本）。
2. `/tmp` 挂载为 erofs 只读。
3. 固定缓冲区按默认 `/tmp/` 长度设计，较长 TMPDIR 会被截断。

## 方案
源码级最小补丁（`patches/0001-src-mat.c.patch`）：
- `Mat_mktemp()` 优先 `getenv("TMPDIR")`，未设置回退 `/tmp`；
- 扩大固定缓冲区 `MAT_MKTEMP_DIR_MAX 256` 容纳较长 TMPDIR；
- 补丁经 `conandata.yml` 的 `patches:` 声明（patch_file 名须与 patches/ 目录实际文件名完全一致），
  由 `conan create` 干净构建验证；
- 复测：`TMPDIR=$HOME/tmp ./test_mat delete test_write_2d_numeric.mat a` → rc=0。

## 验证（matio 1.5.26 实测）
- delete 测试：rc=21 → 0；test_mat 41/41 通过（写 33 + 读 8）；
- conan-verify G1-G4 + L2/L4/L5 全过；finish W3 本地 CI 100%；
- test_package 消费者写读回环（L1）通过。

## 适用边界
- ✅ 库源码硬编码 /tmp 且不读 TMPDIR 的运行时临时文件/目录（如 Mat_mktemp、O_TMPFILE/P_tmpdir 硬编码）。
- ❌ 构建脚本（configure/make）的 /tmp 问题 → 用 E002/E136/E052 环境变量方案。
- ❌ 已遵循 TMPDIR 的 glibc tmpfile/P_tmpdir 路径 → 无需补丁。

## 查重差异（七轴）
- exact_duplicate: 否；causal_duplicate: 否（根因同为 erofs /tmp，但触发点为库内 mkdtemp 而非构建脚本）
- trigger_overlap: 部分（与 E002/E225/E325 同触发面 /tmp 只读）
- solution_overlap: 部分（E002 set-env-var 对外部脚本有效；本方案为库内源码补丁 + 缓冲扩容）
- combination_novelty: 是（源码补丁 + 固定缓冲扩容 + conandata patch 声明验收链）
- boundary_novelty: 是（明确"库内硬编码 vs 构建脚本"边界）
- test_migration_novelty: 是（TMPDIR 复测命令可跨库迁移）
- 关系: similar_to=E002, E215, E225, E325；无 caused_by/prerequisite_of/conflicts_with
- 覆盖: E002 环境变量方案不覆盖库内硬编码场景 → 本条目为部分覆盖后新增差异（路径 B）
