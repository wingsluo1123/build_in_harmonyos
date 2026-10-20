# 供应方 LAPACK 宏与整数 ABI 契约

本草稿申请作为已有知识的修正和补充，编号暂借工具生成的E429-draft-8A28，正式编号由主编决定。

## 与已有知识的差异

最接近条目为同目录`DRAFT-ohos-openblas-lapack310-clapack-prototype-conflict.kv`。
它已识别隐藏字符长度问题，但推荐用旧f2c/CLAPACK原型替换供应方声明，并将两者视为同一ABI。
本条保留诊断，补充真机验证的方案：保留供应方声明和宏，由宏处理符号映射及字符长度，同时检查整数契约。
更换声明后编译通过，本身不证明二进制ABI一致；也不证明每个旧原型都会在运行时出错。

相邻E242讨论Fortran .mod编译器身份，E677草稿讨论LAPACKE传递依赖，
`DRAFT-cmake-makefile-per-target-flags-recursive-audit`包含ILP64配置审计。本条只补充
供应方调用宏、消费方/lapack_int/blasint宽度契约和正反例验证组合，不重复申报既有原理。

## 实际触发与边界

鸿蒙PC armv8，clang15，已发布OpenBLAS0.3.34。2026-10-04新增隔离探针：

1. 使用实际安装的lapacke.h调用五参数dtptri_，编译退出1，报需要7参数。
2. 同一源码改走LAPACK_dtptri/LAPACK_stptri，编译、签名、运行均退出0。
3. 仅语法检查添加LAPACK_ILP64，静态检查同时报LP64_REQUIRED和BLAS_LAPACK_WIDTH_MISMATCH；未执行错配二进制。
4. float/double分别检查上三角packed矩阵逆的三个元素，奇异矩阵INFO=1；两个整数类型实际均4字节。

源码、运行入口、原始诊断及依赖身份位于`archives/k/kaldi-vosk/g20231219/knowledge-reproducer/`。
这是新增复现实证，不冒充适配初期日志。此前SIGTRAP已证实来自OpenFST重复析构，与LAPACK分列。

## 推荐方案

```cpp
#include <lapacke.h>
#include <cblas.h>
#include <cstdint>
using Index = lapack_int;
static_assert(sizeof(Index) == sizeof(int32_t), "LP64_REQUIRED");
static_assert(sizeof(blasint) == sizeof(Index), "BLAS_LAPACK_WIDTH_MISMATCH");
// 按原例程布局调用 LAPACK_dtptri(...) 等供应方入口。
```

本任务消费方要求LP64；其他消费方按其真实索引ABI设约束，不将32位条件推广到全部LAPACK。
宏须与链接的供应方二进制配套。没有该接口时按供应方文档建立包装，或明确迁移LAPACKE。
LAPACK_*与LAPACKE_*接口不同，后者另有布局、工作区、返回值语义。

隐藏长度数量按例程不同：目标头中TPTRI和GESVD各两个字符参数，宏追加两个长度；SPTRF一个；
GETRF无字符参数，不追加长度。不要统一手加两个参数，也不要删除供应方长度声明。

## 验证与推广

```sh
bash archives/k/kaldi-vosk/g20231219/knowledge-reproducer/run.sh /absolute/path/to/openblas/package
```

两个预期编译负例均须匹配诊断，数值判断不用assert。包级补丁0025迁移宏，0026检查整数；
共享/静态各125/125启用断言的上游测试和53消费者通过，含GEMM、LU、SVD、packed运算和奇异输入。
程序数、消费者检查与本探针分列统计。

推广对象为同类C/C++到Fortran LAPACK接入。目前实测Kaldi Vosk及独立探针，未声称第二个实际库完成迁移。
供应方宏并非本轮发明，B2候选增量是对已有推荐的修正及其可复核证据，是否足够由评审确认。
