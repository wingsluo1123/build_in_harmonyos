# phast 1.8 适配 notes

## 上游信息
- 上游：https://github.com/CshlSiepelLab/phast （CshlSiepelLab，BSD-3-Clause）
- tag：v1.8（注：上游 `version` 文件自 v1.7 起忘记 bump，仍写着 v1.6，
  已核对 GitHub v1.8 tag 原始文件与 v1.8 release 修复特征
  `THRESHOLD_BRANCH_LENGTH 1e-8`（src/lib/phylo/phast_trees.c:39）确认内容正确）
- 源码包 sha256：cf940869102cff48bdfbfab6b23c6515eae743959649903174c7e24f21d26b50
- 构建系统：手写 Makefile（非 CMake）。src/ 下分层构建 libphast.a
  （含捆绑 PCRE）+ 约 30 个命令行工具（msa_view/phyloFit/phastCons/phyloP/...）。

## 依赖（W0）
- 唯一运行时依赖：lapack/3.12.1（reference LAPACK+BLAS，flang 设备原生编译）。
  `conan download lapack/3.12.1 -r=ohpcd` 通过（含 OHOS/clang15 二进制包，
  liblapack.a 中 dgeev_/dgetrf_/dgetri_/dgesv_/dgebal_/dgebak_ 六符号全部存在）。
- 上游默认 CLAPACK（f2c.h/clapack.h，-llapack -ltmg -lblaswr -lf2c），
  OHOS 无 CLAPACK → 改链接参考 LAPACK。
- SKIP_LAPACK 绕过路径不可取：会使 phastCons/phyloFit 等核心程序运行期
  die()（R40 适配完整性 + 上游测试 phyloFit/phastCons 套件均无法执行）。

## 关键适配点
1. **整数宽度（最易踩坑）**：CLAPACK 的 f2c.h 定义 `integer` 为
   `long int`（LP64 上 8 字节），参考 LAPACK（flang 默认）INTEGER 是
   4 字节 int。补丁 0001 在 external_libs.h 内直接 `typedef int integer`，
   保证按指针传参的 LAPACK_INT 与 Fortran 侧 4 字节一致。
2. **CLAPACKPATH 强制自动探测**：make-include.mk 无条件置
   `CLAPACKPATH=/usr/local/software/clapack`，导致 lib/Makefile 走
   `ifdef CLAPACKPATH` 分支做 liblinks 符号链接（必然失败）。补丁 0002
   移除自动探测，CLAPACKPATH 未定义 → lib/ 只建 libphast.a。
3. **命令行覆盖构建变量（R33）**：CC/CFLAGS/LIBS/LIBPATH 全部由 conan
   配方经 make 命令行传入。注意 make 惯例：命令行变量会同时抑制
   makefile 内对同名变量的 `=` 赋值与 `+=` 追加，因此 CFLAGS 必须补全
   上游追加项（-I{INC} -DPHAST_VERSION -DPHAST_HOME -I{pcre}
   -fno-strict-aliasing），LIBS 补全参考 LAPACK 链
   （-lphast -llapack -lblas -lFortranRuntime -lFortranDecimal -lm）。
4. **不要命令行传 PHAST**：子 Makefile 靠 `PHAST := ${PHAST}/..` 逐级
   重算根目录，传入会破坏路径推导，保持上游 PWD 推导即可。
5. **man 手册生成**：src/Makefile `all` 目标会对每个 freshly-built 二进制
   跑 `perl help2man.pl`（执行二进制取 --help）。补丁 0003 跳过——man 页
   不属于 conan 包产物，也避免构建期执行二进制的不可控风险。

## 打包内容
- lib/libphast.a（静态，含捆绑 PCRE）
- include/phast/*.h（公共头）
- bin/*（约 30 个命令行工具）→ 软件级 commands.json（R38）

## 上游测试（R51 申报 + 实测回填）
- 清点：test/Makefile 3 个目标（msa_view / phyloFit / phastCons），共 30 项
  `diff --brief` 断言（msa_view 12 + phyloFit 14 + phastCons 4）。
- 实测（鸿蒙真机，签名后产物 bin 加入 PATH）：
  - msa_view **12/12 字节级通过**（exit 0）
  - phyloFit 14 项：2 项失败源于上游参考 jc.mod 过时（旧 1/n 约定 vs 源码
    1/(n-1)，上游 master 参考同样未更新）；其余 12 项为跨 LAPACK/FP 末位
    数值噪声（≤0.025，多例 LNL 逐打印位一致）
  - phastCons 4 项：参考 cons_correct.dat 为旧版输出格式（归一化后 18005
    位置全对齐，Pearson r=0.9988）；elements 边界位移为分数噪声传导
- 结论：**0 项功能性/结构性失败**；全部字节级差异归因于上游参考文件过时或
  跨 LAPACK 数值环境差异，详见 reports/upstream-test-report.md。
- test_package 为消费者验证（5/5 PASS），不替代上游测试统计。
---

**编译结束**: 2026-10-14 20:14
**最终状态**: built
