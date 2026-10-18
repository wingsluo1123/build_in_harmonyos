# DRAFT: clang 的 `<varargs.h>` 是 `#error` 桩——K&R 变参（`va_dcl` + 单参 `va_start`）必须逐入口转 C99 `<stdarg.h>`，编译选项绕不过去

- **Status**: DRAFT
- **出处**: ifmail 2.14tx8.10 适配（2026-10-16，【知识库扩展】PR，分支 `feat/ifmail-2.14tx8.10`）
- **领域**: 编译器/libc 代际差异（pre-ANSI C → C99）
- **agent_id**: 6E98

## 相关既有条目（撞车判定）

查重方式：`ohc-run.py engine "<真实报错串>"` + `grep -in "varargs\|stdarg\|va_dcl" knowledge/graph/index.tsv`。

| 条目 | 它覆盖什么 | 本条增量 |
|---|---|---|
| E063（add-cflags-disable-werror） | 项目开了 `-Werror`（或 `-Werror=implicit-function-declaration` 等）把**警告**升级成错误，建议按类别加 `-Wno-error=*` | **本条的三条错误都不是警告升级来的**：`<varargs.h>` 桩头是 `#error`，`va_dcl` 是语法错误，单参 `va_start` 是宏实参个数错误 —— 关警告一条都消不掉。E063 在此明确不适用，本条要与它区分开，避免有人照着加 CFLAGS 白跑一轮 CI |
| E585 草稿族（tal：`-ansi` → `__STRICT_ANSI__` → musl 隐藏 `strdup` 声明 → C89 隐式 int → LP64 指针截断 → 运行即 SIGSEGV） | 隐式声明导致指针截断、"编译过运行炸" | 同一**后果族**：本条的 forbid_2（自造 `va_start` 宏 / 伪造 varargs.h）会产生同样"编译通过、运行时错读参数"的静默故障；但触发点不同（那条是特性测试宏 + musl 头，本条是 clang 桩头 + K&R 语法），修法也不同 |
| E119 | 同一 TU 双头重定义（sockaddr_storage） | 无关，仅同为"头文件代际差异"大类 |
| E062 | gnulib 的 `FLEXIBLE_ARRAY_MEMBER`/include 顺序 | 无关 |

engine 对本条报错串只命中 E301（Conan `CMake.test()` vs `CMake.ctest()` 的参数路由，Phase B: 0，完全无关）；`index.tsv` 全文 grep `varargs|stdarg|va_dcl` **零命中** ⇒ 真实缺口，独立申报。`similar_to: E063, E585`。

## Scope（何时用）

源码里能 grep 到下列任一特征的 C 项目：

```
va_dcl          va_alist          #include <varargs.h>
va_start(ap);   ← 只有一个实参
fmt = va_arg(ap, char *);   ← 把格式串当第一个省略参数取
```

典型是 1985-1998 年间、带自研 printf 风格日志函数的软件（ifmail、inn、nn、trn、
tin、elm、zmailer、老 sendmail、各类 FidoNet/UUCP/BBS 软件）。
ifmail 2.14tx8.10 实测两处入口：`iflib/lutil.c` 的 `loginf`/`logerr`/`debug`，
`ifcico/respfreq.c` 的 `static add_report`。

**不适用**：已经用 `<stdarg.h>` 的代码；C++ 变参模板/变参宏；只是被 `-Werror`
升级的警告（走 E063）。

## Symptom（真实日志，2026-10-16 OHOS clang 15）

一个 K&R 变参函数一次炸出三条**互相独立**的硬错误，很容易被当成三个问题分别去修：

```
In file included from lutil.c:7:
/Users/.../llvm/lib/clang/15.0.4/include/varargs.h:11:4: error: "Please use <stdarg.h> instead of <varargs.h>"
  #error "Please use <stdarg.h> instead of <varargs.h>"
   ^
lutil.c:147:1: error: expected function body after function declarator
va_dcl
^
lutil.c:155:15: error: too few arguments provided to function-like macro invocation
        va_start(args);
                     ^
/Users/.../llvm/lib/clang/15.0.4/include/stdarg.h:17:9: note: macro 'va_start' defined here
#define va_start(ap, param) __builtin_va_start(ap, param)
        ^
7 warnings and 9 errors generated.
```

转换过程中的连带错误（都是本条的一部分，不是新问题）：

```
# 只改了定义、没改 static 函数的无原型前置声明
respfreq.c:618:13: error: conflicting types for 'add_report'

# 新加的变参包装放在了 #include "lutil.h" 之前 → logerr 先被隐式声明成 int
../iflib/lutil.h:26:6: error: conflicting types for 'logerr'

# 同族：漏 include 项目工具头 → 返回 char* 的函数被隐式声明成 int
lutil.c:33:8: error: incompatible integer to pointer conversion assigning to 'char *' from 'int' [-Wint-conversion]
        myname=xstrcpy(myname);
```

## Root Cause

1. `<varargs.h>` 是 pre-ANSI 机制，C99 已删除。**clang 提供的是只含 `#error` 的桩头**
   （实测 clang 15 `include/varargs.h:11`、Apple clang 17 `include/varargs.h:14`），
   gcc 干脆不提供该头（`fatal error: No such file`）。所以这不是"OHOS 特有"，
   而是所有现代工具链的共性——只是老项目在 glibc + 老 gcc 上还能编过。
2. `va_dcl`/`va_alist` 不是合法 C99 声明 → `expected function body after function declarator`。
3. `<stdarg.h>` 的 `va_start` 是**两参**宏 `va_start(ap, last_named)`，因为它要靠
   最后一个具名参数定位省略参数的起点；K&R 的单参写法自然"实参太少"。
4. 老代码库常常是"半现代化"的：头文件已经写成 ANSI 原型
   （ifmail 的 `iflib/lutil.h` 就是 `void debug(unsigned long,char*,...)`、
   `void loginf(char*,...)`），只有 .c 里的定义还是 `va_dcl`。**只改一边必然
   `conflicting types`**。
5. 隐式声明在 C99 下等价于"返回 int"，赋给 `char *` 就是 int→pointer 转换，
   clang 15 判为 error（`-w` 也压不掉）。

## Workaround / 修复

机械转换，每个入口四步（纯 C，不加任何平台宏，glibc 下同样编译通过）：

```c
/* before (K&R) */                          /* after (C99) */
#include <varargs.h>                    →   #include <stdarg.h>

void loginf(va_alist)                   →   void loginf(char *fmt, ...)
va_dcl                                  →   （删除）
{                                           {
    va_list args;                               va_list args;
    char *fmt;                              →   （删除局部变量）
    va_start(args);                         →   va_start(args, fmt);
    fmt = va_arg(args, char *);             →   （删除）
    vfprintf(stderr, fmt, args);                vfprintf(stderr, fmt, args);   /* 原样 */
    va_end(args);                               va_end(args);                  /* 原样 */
}                                           }
```

多个前置参数的入口，`va_start` 的第二个实参就是**最后一个具名参数**：

```c
/* before */
void debug(va_alist)
va_dcl
{
    va_list args; unsigned long level; char *fmt;
    va_start(args);
    level = va_arg(args, unsigned long);
    fmt   = va_arg(args, char *);
    ...
}

/* after */
void debug(unsigned long level, char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ...
}
```

三件必须一起做的配套动作（缺一就换一种错误继续失败）：

1. **同步声明侧**：头文件的 ANSI 原型、以及 `static void f();` 这种无原型前置声明
   （改成 `static void f(char*,...);`）。
2. **注意插入位置**：新增的变参包装/shim 必须放在"声明了它要调用的函数"的
   include **之后**，否则包装里的调用先生成隐式声明，随后与头文件冲突
   （实测 `conflicting types for 'logerr'`）。
3. **顺手补齐同族缺失的 include**：`<string.h>`（strcmp）、`<stdlib.h>`（exit/abort）、
   项目自己的工具头（ifmail 的 `xutil.h` 提供 `xstrcpy`/`xstrcat`）。否则隐式声明
   会变成 int→pointer 硬错误，看起来像"转换没生效"。

对应补丁：`archives/i/ifmail/2.14tx8.10/patches/0008-iflib-lutil.c.patch`、
`0003-ifcico-respfreq.c.patch`、`0009-iflib-make_new_ref.c.patch`、
`0010-iflib-trap.c.patch`、`0013-iflib-parsedate.y.patch`。

### 禁止做法

| 写法 | 为什么禁止 | 后果 |
|---|---|---|
| `-Wno-error=int-conversion` / `-w` / `-fpermissive` | 三条错误都是硬错误，不是被 `-Werror` 升级的警告；`#error` 桩头与语法错误关不掉 | 白跑一轮 CI（20 分钟起），且把"源码需转换"误判成"编译选项问题"。E063 在此不适用 |
| `#define va_start(ap) ...` / 伪造 `varargs.h` / `-Dvarargs_h` | 等于手写变参 ABI。aarch64/LP64 上省略参数的寄存器与栈布局由**具名参数个数**决定，宏拿不到这个信息 | 编译通过、运行时格式化取值错位（打印垃圾指针/串位），最坏解引用错误地址 SIGSEGV——与 E585 家族同类"编译过、运行炸" |
| 转换后仍留 `va_start(ap);` | 漏改 | 同一文件继续 `too few arguments` |

## 验证（可复算）

```sh
cat > /tmp/vargs-kr.c <<'EOF'
#include <varargs.h>
#include <stdio.h>
void f(va_alist)
va_dcl
{
    va_list ap; char *fmt;
    va_start(ap);
    fmt = va_arg(ap, char *);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}
int main(void){ f("n=%d s=%s\n", 42, "x"); return 0; }
EOF
clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -c /tmp/vargs-kr.c -o /dev/null   # 3 errors
cc -c /tmp/vargs-kr.c -o /dev/null                                                     # Apple clang 17: 同样报错
# 机械转换后：
#   <varargs.h> → <stdarg.h>；void f(va_alist)/va_dcl → void f(char *fmt, ...)；
#   va_start(ap); → va_start(ap, fmt);  删掉 fmt = va_arg(...)
clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -c /tmp/vargs-c99.c -o /dev/null  # rc=0
cc /tmp/vargs-c99.c -o /tmp/vargs-c99 && /tmp/vargs-c99                                # 输出 n=42 s=x
```

实测结论（2026-10-16）：K&R 版在 OHOS clang 15 报 3 条错误、在宿主 Apple clang 17
报同样前两条 ⇒ 与 OHOS 无关，是 clang 家族通病；C99 版 rc=0 且宿主运行输出
`n=42 s=x`，证明格式串与两个省略参数都取对（语义等价，不只是"编过"）。

真机侧的可观测验证：转换是否正确**不能只看编译通过**（错读参数不会报错），要看
格式化结果。ifmail 的鸿蒙特有测试 OHOS-2（`archives/i/ifmail/2.14tx8.10/
test_package/test_ifmail_ohos.sh`，7 项）跑 `ifindex -x21 -I <fixture>`，
断言调试文件里四种不同签名的输出取值正确：

```
Initialize 1 nodelists                                  ← debug(20,"...%d", n)
opened nodelist "<path>/nodelist.266"                   ← debug(20,"...%s", str)
start ifindex ver 2.14-tx8.10 of <date>, verbose 0x001fffff   ← %s %s %s + %08lx
put: 2:5020/230.0 as (0,135)                            ← %u %u %u %u + %d + %lu（六参）
```

其中 `0x001fffff` = 2^21-1（`-x21` 的 verbose 位图）、`135`/`266` 是夹具 nodelist
的行字节偏移（61+74=135、135+63+68=266，Boss 行不建索引项），都能从输入推导。

## Prevention

1. 接手 1990s C 项目，第一件事 `grep -rn 'va_dcl\|va_alist\|<varargs\.h>'`，
   把变参入口数点清楚再动手（ifmail 是 4 个入口 / 2 个文件）。
2. 见到 `conflicting types for 'xxx'`，先看**两边**：多半是头文件已 ANSI、
   定义还 K&R，或前置声明无原型。
3. 新增变参包装时，把它放在相关 include **之后**。
4. 不要用编译选项去压这一类错误；也不要用宏伪造变参机制。
5. 转换后一定要有"取值正确"的运行期断言，别只满足于编译通过。

## References

- `archives/i/ifmail/2.14tx8.10/patches/{0003,0008,0009,0010,0013}-*.patch`
- `archives/i/ifmail/2.14tx8.10/test_package/test_ifmail_ohos.sh`（OHOS-2）
- `archives/i/ifmail/2.14tx8.10/notes.md` §4（逐补丁根因表）、§6（验证矩阵）
- C99 7.15 `<stdarg.h>`；clang `include/varargs.h`（`#error` 桩）
