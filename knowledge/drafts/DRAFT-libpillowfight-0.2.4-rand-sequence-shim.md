# DRAFT — 种子采样 C 算法（srand/rand）在 OHOS/musl 与 glibc 参考环境 rand() 序列不同 → 字节级测试整体漂移

- **软件**：libpillowfight 0.2.4
- **任务**：`libpillowfight-0.2.4-r04-upstream-pytest-full-pass-env-alignment-pc1-35-20261015T093500Z`
- **状态**：DRAFT（配对 `DRAFT-libpillowfight-0.2.4-rand-sequence-shim.kv`）
- **编号**：`DRAFT-libpillowfight-0.2.4-rand-sequence-shim`（待人工审核后分配正式 E 编号）

## 1. 现象

带 seed 的确定性随机算法（如 ACE：`srand(seed)` 后 `rand()%max_x/%max_y` 采样）在
OHOS 设备端跑上游字节级测试（`out_img.tobytes() == expected_img.tobytes()`）时整体
漂移失败：同一 seed 下无损输出与参考图 639 万像素（max 88）不同，TEST_DIFF 592 万
像素（max 45）——不是 ±1~2 边界翻转，而是全局差异。

## 2. 根因

设备 libc（OHOS/musl）与参考环境（glibc）的 `rand()/srand()` 实现不同：
实测 `srand(12345)` 后前 20 项 `rand()%1000`：
- 设备（musl）：`138,396,541,857,934,4,106,...`
- glibc 语义参考：`808,348,265,499,710,525,670,259,...`

同一 seed 下采样点集合不同 → 算法输出整体漂移。这是**序列语义差异**（非符号缺失，
不报错、不改接口），只在字节级测试中显现。

## 3. 设备可执行复现

```sh
python3 - <<'PY'
import ctypes
libc=ctypes.CDLL("libc.so"); libc.srand.argtypes=[ctypes.c_uint]; libc.rand.restype=ctypes.c_int
libc.srand(12345); print([libc.rand()%1000 for _ in range(20)])
PY
# 与 glibc random_r（TYPE_3）精确移植序列对照；或直接对拍 C 程序（LD_PRELOAD shim 前后）
```

## 4. 处置（libpillowfight R04 实测有效：漂移 5.92M→1.45M px）

以 LD_PRELOAD 提供 glibc 语义 `srand()/rand()`（忠实移植 glibc random_r.c：TYPE_3
加性生成器，srandom_r 表填充 `state[i]=(16807*state[i-1])%2147483647` 后 310 次预热，
random_r 前后指针加和取 `val>>1`），不改上游源码。忠实性校验：C 程序 LD_PRELOAD shim 后
`rand()*20` 与 glibc 参考逐值一致。

```sh
LD_PRELOAD=/path/to/glibc-rand-shim.so python3 -m pytest tests/tests_ace.py -v
```

## 5. 边界与反例

- **与 E531 的区别**：E531 是 qsort_r **符号缺失**（未定义引用，链接期报错）；本条是
  rand() **序列语义差异**（符号存在但序列不同，运行期字节级测试暴露）。
- **与 drand48_r 草案的区别**：drand48_r 是结构体/符号缺失；本条是语义差异。
- **反例**：参考环境本身即 musl（或测试不比对参考产物）时不需要 shim。
- **限制**：若参考环境 rand 语义不可知（非 glibc），shim 只能部分收敛，残余需裁决。

## 6. 复用提示

凡用 rand()/srand() 做种子采样/随机化的 C/C++ 算法（图像、音频、ML、仿真），其测试
字节级比对参考环境产物，且运行于 OHOS/musl 设备：先取证 rand 序列差异，再以 glibc
语义 shim 对齐运行环境，量化漂移收敛后仍残余则交分析端裁决。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| 采样点 | `_ace.c:414 srand(seed)`、`:133/134 rand()%max_x/%max_y`（seed 12345/0xDEADBEE/0xBEEDEAD） |
| 序列对照 | `exp-rand-probe.log`：设备 20 项 mod1000 与 glibc 参考不一致 |
| shim 校验 | C 程序 LD_PRELOAD shim 后 `rand()*20` == glibc random_r 精确移植（逐值一致） |
| 对齐效果 | ace TEST_DIFF 5917771→1449939 px、all_1 4793104→196784 px |
