# E697 — plain char 承接 getopt(3) 返回值：aarch64 上 char 无符号，-1 哨兵永不成立

## 错误特征

带选项的子命令全部退化为 usage 报错（程序没有崩溃、没有编译错误，只在运行时"参数像没传"）：

```
$ ./vitunes -e check -s t1.flac
vitunes: usage: -e check [-rsd] file1 [ file2 ... ]
$ ./vitunes -e flush -t txt
vitunes: usage: flush [-t format]
$ ./vitunes -e flush -t
flush: option requires an argument: t
vitunes: usage: flush [-t format]
```

若子命令的 `switch` 默认分支不退出，则表现为**无限循环 / 100% CPU 挂起**（同族哨兵失效）。

探针复现（把 `char ch` 版与 `int ch` 版的 getopt 循环打印出来）：

```
# char ch（未修复）
DBG inner ch=115('s') optind=2      <- 正常解析到 -s
DBG inner ch=255('ÿ') optind=2      <- getopt 返回 -1 被截成 255，循环条件 != -1 恒真
vitunes: usage: ...                 <- 第二次迭代落入 default 分支
# int ch（修复后）
DBG inner ch=115('s') optind=2；after: optind=2 nfiles=1   <- 正常结束
```

## 触发条件

- 平台: OHOS / HarmonyOS PC（aarch64，clang 15：`clang -dM -E -` 含 `__CHAR_UNSIGNED__`，
  `CHAR_MIN == 0`）；任何 plain char 无符号的目标（ARM 系默认）
- 阶段: runtime（编译完全正常，只在运行命令行参数解析时暴露）
- 典型代码: `char ch; while ((ch = getopt(argc, argv, "…")) != -1) { … }`
- 同族: `char c` 承接 `getc()/fgetc()/getchar()` 后与 `EOF(-1)` 比较（见关联条目）、
  任何把 `-1/EOF` 当哨兵存入 plain char 的读取循环

## 根因分析

`getopt(3)` 返回 **int**，用 `-1` 表示"没有更多选项"，POSIX 明确要求接收变量是 int。
而 plain `char` 的符号性由实现定义：x86 上默认有符号，aarch64/ARM 上默认**无符号**。
于是 `-1` 存入 `char` 变成 `255`，表达式 `(ch = getopt(...)) != -1` 中 `ch` 经整型提升为
`255 != -1` → **恒为真**，循环不会因为"选项解析结束"而退出：

1. 下一次迭代 getopt 仍返回 -1（无更多选项），`ch` 又是 255；
2. 控制流落入 `switch` 的 `default:`（或 `case 'h': case '?':` 兜底），多数实现直接
   `errx(1, "usage: …")` 退出——用户看到的就是"选项没被识别"；
3. 若 `default` 不退出（例如只 `continue`），则变成死循环（同 E8543 的 EOF 变体）。

同一份源码在 x86 Linux 上一切正常，因此该缺陷**只在移植到 aarch64/OHOS 时才暴露**，
且与 `optreset`/`optind` 重置逻辑无关（musl 对 `optind = 0` 的重新初始化是支持的，
探针已验证重置后能正确解析 `-s`）。

## 解决方案

### 推荐方案

把接收 `getopt(3)` 返回值的变量声明为 `int`：

```c
-   char   ch;
+   int    ch;
    …
    while ((ch = getopt(argc, argv, "rsd")) != -1) { … }
```

vitunes 2.3 实测：`ecmd_check`/`ecmd_flush`/`ecmd_tag` 三处 `char ch` → `int ch`
（`archives/v/vitunes/2.3/patches/0001-e_commands.c.patch`）；修复后
`-e check -s <file>` 正常输出 taglib 提取的 Artist/Album/Title/Track/Year，`-e flush -t "%Y"`
正常导出数据库。

排查动作（成本极低，建议对每个移植到 ARM 的 C 项目做一次）：

```bash
clang -dM -E - </dev/null | grep -c CHAR_UNSIGNED        # 1 = plain char 无符号（本机实测 1）
grep -n "getopt(" *.c                                     # 找所有 getopt 调用点
grep -nE '^[[:space:]]*char[[:space:]]+[a-zA-Z_]+[[:space:]]*;' *.c   # 找 char 声明，交叉核对
```

### 禁止做法

- ❌ 用 `-fsigned-char` 全局翻转 char 符号性来"修好"：会同时改变所有依赖 plain char 无符号的
  代码（位运算/字节序处理）与库 ABI 假设，属于掩盖而非修复；
- ❌ 改成 `while ((ch = getopt(...)) != 255)` 之类——把哨兵写死成截断值，换架构又会错；
- ❌ 把 `-1` 比较改成 `!= EOF`、`!= '\377'` 等等价写法（同样是拿 char 存 int 返回值）。

## 验证

```bash
# 平台符号性（命中本条目）
clang -dM -E - </dev/null | grep CHAR_UNSIGNED           # #define __CHAR_UNSIGNED__ 1

# 修复验证：带选项的子命令必须真正解析到选项
./<prog> -e check -s <file>      # rc=0 且输出内容（不再是 usage）
./<prog> -e flush -t "%Y"        # rc=0 且输出数据库行
```

vitunes 实测结果（conan create 内 test_package，11/11 断言通过，含
`-e check -s` 输出 `Artist: 'Test Artist'`、`-e flush -t` 导出条目、`-e update` 复扫）：

```bash
$ python3 test_package/test_vitunes.py <pkg>/bin/vitunes
PASS: vitunes -e check -s shows the tags read via the taglib C API
PASS: vitunes -e flush dumps the database entries with their tags
11/11 checks passed
```

## 适用边界

- 适用：所有把 `getopt(3)`（含 `getopt_long` 的短选项返回值）存入 plain `char` 的 C 程序，
  尤其从 x86 移植到 aarch64/OHOS 的项目；
- 适用：同族的 `char c` 承接 `getc/fgetc/getchar` 与 `EOF` 比较、`char` 承接返回 `-1` 的
  其它 API（如 `recv`/`read` 的错误哨兵）等——排查方法相同；
- 不适用：变量本身就是"字节数据"语义（如 `unsigned char` 缓冲区元素、`uthash` 键），
  那里 plain char 无符号反而是期望行为，不应改；
- 不适用：使用 `-fsigned-char` 编译整个项目的工程（那类工程的行为基线与本条目不同）。

## 查重结论（六维对照）

最相近条目：**knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop**
（looktxt 1.4.1：`char c` 承接 `getc()` 与 EOF 比较 → 扫描状态机死循环、测试 rc=124）。
根因同源（plain char 无符号使 -1/EOF 哨兵失效，同族还有 E419 的"plain char 作为有符号 8 位
样本"数值差 256）。

| 维度 | DRAFT-8543（looktxt，getc/EOF） | 本条目（vitunes，getopt） | 是否重复 |
|------|-------------------------------|--------------------------|---------|
| 根因 | plain char 无符号 → -1 不可表示 | 同 | 重合 |
| 症状 | 死循环挂起 rc=124、100% CPU | **选项解析失败报 usage**（不是挂起，default 分支会退出） | **不同** |
| 触发 API | `getc()/fgetc()` + `c == EOF` | `getopt()` + `ch != -1` | **不同** |
| 定位方法 | `grep getc(` + char 声明交叉核对 | 打印 getopt 返回值/循环迭代（探针实测 255 vs 115） | **新增** |
| 修复 | 接收变量改 int | 同为改 int（本次涉及 3 处子命令） | 相同 |
| 验证 | `timeout 25 … --test` 从 124 → 0 | 带选项子命令从 usage → 正常输出（11/11 断言） | **新增** |

其他查重动作：

- `grep -rln "getopt" knowledge/graph/ knowledge/doc/ knowledge/drafts/` → 正式条目 E038（groff 宏）
  与 E503 是别的问题，无 getopt 返回值类型条目；
- `grep -rln "unsigned char 默认\|char 默认 unsigned" knowledge/` → 仅 DRAFT-8543 系列；
- 结论：**部分重复后保留**。重合点是根因（char 符号性），差异与新增价值是"getopt 这一更常见
  API 面 + 症状不是挂起而是静默退化报 usage"、"用返回值打印定位"的诊断法，以及子命令级验证证据。

## 关联条目

- 部分重复: knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop（getc/EOF 变体）
- 同源实现定义行为: E419（plain char 有符号 8 位样本导致数值差）
- 具体复现: archives/v/vitunes/2.3（补丁 0001 + notes.md）
