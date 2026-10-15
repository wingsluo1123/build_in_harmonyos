# DRAFT-9006-aarch64-fp-contract-1ulp-vs-x86

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9006-aarch64-fp-contract-1ulp-vs-x86.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9006: AArch64 默认 FMA 收缩导致浮点结果比 x86 差 1 ULP —— "逐字节比对参考输出"型上游测试的必踩陷阱

- 条目主题：aarch64 上 clang 默认把 `a*b+c` 收缩成 FMA（少一次中间舍入），
  使浮点打印值与 x86 参考差 1 ULP；对"与参考输出 diff"的上游测试必须
  `-ffp-contract=off` 才能对齐。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12

## 适用场景

- 上游测试含"把程序输出与仓库内参考文件 diff"的用例，在 aarch64 上失败；
- 失败形态极有辨识度：**只有浮点列的最后 1~3 位小数不同**，其余字段（坐标、命中集合、
  整数字段、字符串）完全一致：

```
< ... 254 53.837402 + ACTGCATAATTCTCTTACTGTCATG----CCATCCGTAAGATGCT
> ... 254 53.837406 + ACTGCATAATTCTCTTACTGTCATG----CCATCCGTAAGATGCT
```

- 数量级判断：差值 4e-6 ≈ 该量级 float32 的 1 个 ULP。

## 根因

- aarch64 **强制**有 FMA；x86-64 只有 `-mfma` 且编译器选择收缩时才有。
- C 标准默认 `-ffp-contract=on`：`a*b+c` 合并为一条 FMA，省掉中间乘积的舍入。
- 故同一份源码、同一算法在两种架构上得到 1 ULP 级差异；整数运算与比较逻辑不受影响。

## 处置

```cmake
set(CMAKE_C_FLAGS       "${CMAKE_C_FLAGS} -ffp-contract=off")
set(CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -ffp-contract=off")
```
Conan 配方侧：
```python
tc.extra_cflags.append("-ffp-contract=off")
tc.cache_variables["CMAKE_Fortran_FLAGS"] = "... -ffp-contract=off"
```

排查顺序（避免误判成"转译层有 bug"）：

1. 确认差异**只在浮点末位**、只出现在少数行 —— 若对齐/命中集合也变了，才是算法问题；
2. 加 `-ffp-contract=off` 重建并重跑 diff；
3. 仍不等再检查 `-ffast-math`/`-Ofast`、`-funsafe-math-optimizations`，
   以及 libm 差异（`log/exp` 在 glibc/musl 间本就不同）。

## 证据（真实执行）

pftools 3.2.12（`pfsearchV3` 打印 6 位小数归一化分数）：

| 状态 | `test_V3_output.sh`（与 `tests/examples/test_V3.out` 逐字节比对，1959 行） |
| --- | --- |
| 未加 `-ffp-contract=off` | **失败**：43 行仅浮点第 8 列不同（如 53.837402 vs 53.837406） |
| 加 `-ffp-contract=off` | **通过**：`diff` 退出码 0；CTest **6/6** 通过 |

## 推广价值

- 任何"数值输出与参考文件比对"的 x86 原生库（生物信息、数值计算、编解码、图形）在 aarch64
  适配时先加 `-ffp-contract=off`，避免把 1 ULP 差异误判为 SIMD/转译层缺陷。
- 与 DRAFT-9005（sse2neon 转译）配合：前者保证"算得对"，本条目保证"打印得一样"。

## 查重关键词

-ffp-contract、FMA 收缩、1 ULP、aarch64 浮点差异、逐字节 diff 失败、
test_V3.out、浮点末位不同、-fno-fast-math、truth file 比对
