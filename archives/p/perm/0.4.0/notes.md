# perm 0.4.0 适配笔记

## 结论速览
- **上游**：`code.google.com/p/perm/`（**Google Code 已关站**）→ 源取 Debian 源包 orig
- **它是什么**（按源码实测）：**基于种子模式的短读比对工具**（C++，43 个 .cpp，含 OpenMP 并行），
  `Source/PerM.cpp` 是主程序
- **依赖**：**零外部依赖** ✓（上游 `Source/makefile` 的 `LIBS = -lm -lstdc++`；
  Debian control 里的 `libbsd-dev` 是 Debian 侧补丁所需，用 orig 源不需要）
- **产物**：`bin/perm`（musl 动态 ELF64/AArch64，**11,241,472 字节**）
- **上游测试**：自带 **3 个用例入口**（`Source/ColorSpaceRead.h` 声明的 `testShift64Bit`、
  `testLongBases2Colors`（两参）、`testLongBases2ColorsCases`（零参）；`PerMTest.cpp` 的 `main()`
  调用 `Cases()` → 实际覆盖 2 个，第 3 个上游自己注释掉）→ **真编、真跑** ✓（语义如实披露，见下）
- **状态**：built（本地 conan create 全绿：编译 ✓ + 自带测试真跑 ✓ + 消费者 5/5 ✓）

## 构建与适配要点

### 1) Debian orig 是**两层目录**：`perm_0.4.0/Source/…`
conan 的 `strip_root=True` 只剥一层 → 带 makefile 的源码仍在 `<source>/Source` 下，源码根跑 make 会：
```
make: *** No targets specified and no makefile found.  Stop.
```
→ 配方自动探测（存在 `<source>/Source/makefile` 就用它当构建目录），比写死路径稳。

### 2) 上游 makefile 硬编码 `g++`，且 CFLAGS 带 `-static`
```
CFLAGS =  -ggdb -Wall -fopenmp -static
CC = g++ -O2 $(CFLAGS)
```
→ 命令行传 `CC="<clang++> -O2 -Wall"` **整体覆盖**（make 命令行变量优先级最高）：既换掉本机不存在的
`g++`，又摘掉 musl 下会与共享库冲突的 `-static`。**不改上游 makefile。**

### 3) 现代 clang 拒绝的两处"过时写法"（最小等价修正）
| 位置 | 上游写法 | 报错 | 修正 |
|---|---|---|---|
| `MappingResult.h:265,275` | `m[12].QScores == '\0'` | `comparison between pointer and integer ('char *' and 'char')` | `(!p \|\| p[0] == '\0')` —— 与同文件里上游自己的 `caRef[0] == '\0'` 写法一致，语义不变 |
| `PerMTest.cpp:10` | `testLongBases2Colors()`（零参） | `no matching function for call to 'testLongBases2Colors'` | 改为上游自己的零参入口 **`testLongBases2ColorsCases()`**（`ColorSpaceRead.cpp:402`，内部用固定用例调两参版本）——即**上游测试过时了**，改调用即可真跑，不是跳过 |

### 4) 上游自带测试的**真实语义**（如实披露）
`PerMTest.cpp` 的 `main()`：
```c
int main(int argc, char* argv[]) { /*testShift64Bit();*/ testLongBases2ColorsCases(); return 0; }
```
→ **固定 `return 0`、无输出** ⇒ 本项证明"可编、可跑通"，**不代表有 N 条断言全过**。配方里显式打印这条
说明（`[added tests] ② 如实记录语义…`），既不跳过、也不夸大。

## 上游测试结果（本地实测）
```
[patch] MappingResult.h：char* 与 '\0' 的比较改为 (!p || p[0]=='\0')（等价最小修正，语义不变）
[patch] PerMTest.cpp：过时的零参调用 testLongBases2Colors() → testLongBases2ColorsCases()
[added tests] 编译上游测试程序：42 个源文件
[added tests] ① 上游自带测试程序 PerMTest 编出并真跑通 ✓（rc=0，输出 0 字节）
[added tests] ② 如实记录语义：…main() 只调用 … 并固定 return 0（不断言返回值）
```

## 消费者校验
`test_package/check_perm.py` **5 项，全部离线**：产物齐备 / ELF 头自检（ELF64、machine=0xB7）/
`perm`（无参）真跑有输出（首行 `PerM (Efficient read mapping with periodic full sensitive seeds)`）/
许可证（**上游 orig 未附** → 如实记录）/ 证据。实测 `checks=5 fails=0` / `RESULT: PASS`。

## 许可证说明（如实）
上游 orig 里**没有** LICENSE/COPYING 文件 → 配方 metadata 按 Debian control 标 `GPL-3.0-or-later`，
但**未随包许可证文件**（消费者校验里如实记录，不伪造）。
