# E999 draft — aarch64 `char` 无符号：EOF 哨兵比较永远为真，读循环死转

> 草稿条目（draft: true），待主编审核后提升为正式 E 编号。
> 结构化数据：[E999-draft-aarch64-unsigned-char-eof-sentinel.kv](E999-draft-aarch64-unsigned-char-eof-sentinel.kv)
> 发现来源：plast 2.3.2 在 HarmonyOS aarch64 真机上 `testFastaOutputFrame` 挂死。

## 错误特征

编译期（clang 会直接给出这条线索）：

```text
CommonOsImpl.hpp:80:77: warning: result of comparison of constant -1 with expression of type
'char' is always true [-Wtautological-constant-out-of-range-compare]
```

运行期（没有报错，只有“不返回”）：

```text
进程 CPU 持续占用、无输出、无崩溃，直到被外部 kill
```

## 触发条件

三个条件同时成立：

1. 源码把 `fgetc()` / `getc()` / `gzgetc()` 的返回值存进 **`char`**（而不是 `int`）；
2. 代码用 `EOF`（-1）作为该变量的终止哨兵；
3. 该哨兵**真的会被走到**——典型是“缓冲区限长读取后跳到行尾”的循环遇到文件结尾。

第 3 条很关键：这类代码在绝大多数输入上都正常，只有**最后一行没有换行符**、
或读取长度刚好填满缓冲区时才会暴露。

aarch64 的 `char` 默认**无符号**（x86 默认有符号），`char c = fgetc(f)` 在 EOF 处得到
`(char)-1 == 255`，于是 `c != EOF` 恒为真，`c = fgetc(f)` 又一直返回 EOF，
循环永不退出。

## 影响范围

- 任何年代久远、以字节为单位读文件的 C/C++ 源码；
- 表现为“编译通过、大部分测试通过、某个大数据集上莫名卡住”，极易被误判为
  性能问题或文件系统问题；
- 同一份源码在 x86 上用 `-std=c++14` 试编**完全正常**，跨平台排查时容易走偏。

## 定位命令

```bash
# 1) 先扫源码：把字节读进 char 的地方
grep -rn --include=*.c --include=*.cpp --include=*.h --include=*.hpp \
     -E '(char|int8_t)[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=[[:space:]]*(fgetc|getc|gzgetc)[[:space:]]*\(' .

# 2) 构造“最后一行无换行”的输入复现
printf 'x\n' > /tmp/probe.txt && printf 'no-newline-tail' >> /tmp/probe.txt

# 3) 构建日志里直接搜这条 warning，它是编译期就能拿到的线索
grep -n "tautological-constant-out-of-range-compare" build.log
```

## 推荐方案（priority 1）

把哨兵变量放宽成 `int`，并在用 `char` 值做初值时显式 `unsigned char` 转换，
避免符号扩展：

```diff
-            /** we skip all characters until we reach the next '\n'. */
-            if (result > 0)  {  for (char c = tmp[result-1];  c !='\n' &&  c!=EOF;  c = fgetc (_handle))  {}  }
+            /** we skip all characters until we reach the next '\n'.
+             *  Note that 'c' must be an int: fgetc returns EOF (-1) at end of
+             *  file and comparing it through a plain 'char' only works where
+             *  char is signed; on architectures where char is unsigned (arm64
+             *  for instance) the comparison never matches EOF and the loop
+             *  would spin forever on a last line without any '\n'. */
+            if (result > 0)  {  for (int c = (unsigned char) tmp[result-1];  c !='\n' &&  c!=EOF;  c = fgetc (_handle))  {}  }
```

实测案例：plast 2.3.2 `src/os/impl/CommonOsImpl.hpp:80`，输入 `test/db/sapiens_1Mo.fa`
（表头 115 字符 > `commentMaxSize=100`，且文件末尾无换行）。修复前该测试进程
占用 12 分钟 CPU 不退出；修复后整轮单测 `OK (96 tests)`。

该补丁可向上游提交（P005）：`int` 才是 `fgetc` 的返回类型，原写法在任何平台上都是错的。

## 回退方案（priority 2）

当声明无法改动（例如字段出现在 ABI 可见的结构体里）时，给循环加一个与哨兵无关的
退出条件：

```c
int guard = 0;
for (char c = tmp[result-1]; c != '\n' && c != EOF; c = fgetc (handle))
{
    if (++guard > MAX_LINE_SKIP || feof (handle))  { break; }
}
```

代价：只是让死循环变成“提前截断”，读位置与预期仍可能不一致，属临时兜底。

## ⛔ 禁止

```text
-fsigned-char          # 禁止：全局翻转 char 符号性
-funsigned-char        # 禁止：同上，方向相反
-Wno-tautological-constant-out-of-range-compare   # 禁止：压掉定位该 bug 的诊断
#define EOF ...        # 禁止：重定义 EOF
```

理由：`char` 的符号性是**整个翻译单元**的属性，全局翻转会波及字符串处理、
查表、比较等所有 `char` 用法，用一个 bug 换一类 bug；而压掉诊断等于扔掉了
编译期唯一能指向该行的线索。

plast 2.3.2 的构建日志里**已经**打印过这条 warning 却没有被处理——这正是本条目的
实际教训：aarch64 移植时，`-Wtautological-constant-out-of-range-compare`
应当被逐条当线索排查，而不是当成噪声。

## 关联

- **E419** — *Target plain-char signedness can change INT8 API results without changing
  stored bytes*：同根条目，E419 讲的是 plain char 符号性导致**结果字节相同但取值不同**；
  本条目讲的是它导致**控制流永不退出**（EOF 哨兵失效），phase 与 error signature 均不同。
- **既有草稿 `DRAFT-8543-plain-char-eof-sentinel-infinite-loop`**：**同一模式**（`char`
  承载 `getc`/`fgetc` 结果与 EOF 比较 → 无符号目标上死循环），`similar_to` 亦指向 E419。
  本条目不主张新模式，新增的是本库的具体证据：plast 2.3.2 的触发条件
  （表头 115 字符 > `commentMaxSize=100` 且文件末行无换行）、编译器
  `-Wtautological-constant-out-of-range-compare` 线索在既有构建日志中已出现却未被处理、
  以及 `int c = (unsigned char) tmp[...]` 这一取初值的写法边界。
- **同类草稿**：`E999-draft-aarch64-unsigned-char-negative-index`（同一根因的另一种表现：
  负值被当作数组下标）。两者错误特征与阶段不同，分别可独立匹配。
- **P005** — 补丁必须可向上游提交
- **P007** — `-Werror` 禁用应精准到具体 warning 类别（本条禁止用压诊断代替修代码）
- **P013** — 平台限制必须降级而非绕过

---
*2026-10-15 · 来源：plast 2.3.2 适配（archives/p/plast/2.3.2/patches/0009-fgetc-eof-unsigned-char.patch）*
