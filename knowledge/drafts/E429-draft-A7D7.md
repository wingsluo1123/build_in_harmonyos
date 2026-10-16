# E429-draft-A7D7: 手写 Makefile 的 `uname` 平台闸不识别 HarmonyOS

> 来源：xcwd `0-2.gbpe2c777c` 适配（OHOS PC aarch64）。本条目是**类级可复用方案**，不是某一库的补丁说明。

## 错误特征

```console
$ make CC=clang
Makefile:20: *** Operating System not supported..  Stop.
```

- 报错由 **make 自己**在**解析阶段**抛出（`$(error ...)`），不是编译器报错：日志里没有任何 `clang -c` 行，源码一行未编。
- `Makefile:NN` 的行号随项目不同；`Stop.` 后缀与双点 `..` 是 make 的固有格式。
- 触发前的 Makefile 通常长这样（xcwd 实例，行号即上游真实行号）：

```make
UNAME:=$(shell uname)          # L7  解析期取系统名
ifeq ($(UNAME), Linux)         # L13
    CFLAGS += -DLINUX          # L14 平台宏挂在分支内
else
    ifeq ($(UNAME), FreeBSD)   # L16
        CFLAGS += -I/usr/local/include/ -DBSD
        LDFLAGS += -L/usr/local/lib -lutil
    else
        $(error Operating System not supported.)   # L20
    endif
endif
```

## 触发条件

- 构建系统：**纯手写 Makefile**（无 `configure`、无 `CMakeLists.txt`、无 `meson.build`）。带 configure 的项目走 `config.guess`（见 E007），CMake 走平台模块（见 E092），不会命中本模式。
- 平台判定发生在 **make 解析期**：`$(shell uname)` / `$(shell uname -s)` / `$(shell uname -m)`。
- 目标平台名不在上游写死的列表里。HarmonyOS PC 实测 `uname -s` → `HarmonyOS`（`uname -a` = `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox`）。
- 典型项目类型：suckless 风格单文件工具、平台专用 CLI（X11 客户端、终端/窗口管理小工具）。

## 根因

1. make 解析期执行 `$(shell uname)`，把结果当作**普通字符串**与作者写死的系统名做 `ifeq` 比较。
2. `HarmonyOS` 既不等于 `Linux` 也不等于 `FreeBSD`/`Darwin` → 落入 `else` → `$(error ...)` 在执行任何编译规则前终止。
3. **关键认知**：HarmonyOS 的用户态是 **Linux 兼容面** —— `/proc`、`glob(3)`、`readlink(2)`、`access(2)`、bionic libc 均可用；源码里 `#ifdef LINUX` 分支通常才是行为正确的分支。平台闸缺的是"作者没听说过这个系统名"，**不是**缺少一份新平台实现。
4. 因此正确的最小干预是**让上游自己的 Linux 分支被选中**，而不是新增平台代码。

## 解决方案

### 推荐：命令行覆盖平台变量（`make-platform-variable-override`，零补丁）

原则：只覆盖 **上游 Makefile 自己拥有的构建变量**，源码与 Makefile 保持逐字节不变。

```python
# conanfile.py build() 示意（R33：编译器取自 Conan conf，不用裸 $CC）
cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
cflags = " ".join([UPSTREAM_CFLAGS, "-DLINUX", *include_flags])   # 上游标志 + 分支宏 + Conan -I
ldflags = " ".join([*lib_dirs, "-lX11"])                          # Conan -L + 上游库
self.run(f"make -j1 UNAME=Linux CC={shlex.quote(cc)} "
         f"CFLAGS={shlex.quote(cflags)} LDFLAGS={shlex.quote(ldflags)}",
         cwd=self.source_folder)
```

**两个必须同时做对的动作**：

| # | 动作 | 不做会怎样 |
|---|------|-----------|
| 1 | 传 `UNAME=<上游已知的 Linux 类系统名>` | make 解析期直接 `$(error)`，一行不编 |
| 2 | 若同时传了命令行 `CFLAGS`，**必须重述**该分支追加的宏（`-DLINUX`） | 命令行变量覆盖 makefile 内 `CFLAGS += -DLINUX`，宏被静默丢弃。两条 `#ifdef` 分支往往都定义了同名函数 → **不报错**，产出"能编能链但平台功能分支为空"的二进制（衔接 **E14411**：丢的正是 Makefile 内定义的宏） |

### 回退：最小补丁追加分支（`patch-platform-gate-branch`）

适用于平台名不是 make 变量（硬编码进源码/脚本），或该分支还决定链接库（如 FreeBSD 的 `-lutil`）：

```make
@@
     ifeq ($(UNAME), FreeBSD)
         CFLAGS += -I/usr/local/include/ -DBSD
         LDFLAGS += -L/usr/local/lib -lutil
+    else
+        ifeq ($(UNAME), HarmonyOS)
+            CFLAGS += -DLINUX
+        else
             $(error Operating System not supported.)
+        endif
     endif
```

补丁必须由 `ohc-run.py refresh-patch --auto` 生成（R3），保持上游缩进/风格，且**不得删除**其它平台分支（R8）。

### 禁止

| 禁止做法 | 原因 | 后果 |
|---|---|---|
| `sed -i` 改 Makefile / 生成物绕过平台闸 | 改动不可复现、不在 `conandata.yml` 声明、无法生成补丁审计（R2/R6/R3） | 下个版本重踩；归档知识丢失；审计判 P0 |
| 传 `UNAME=Linux` 但命令行 CFLAGS 不带分支宏 | 静默丢弃 `CFLAGS += -DLINUX`（同 E14411） | 功能分支为空却可编可链，消费者测试可能仍通过 → 最危险的失败形态 |

## 适用范围与输入输出

| 项 | 内容 |
|---|---|
| 输入 | ① 手写 Makefile（含 `uname` 平台闸）；② 本机 `uname -s` 实际值；③ 上游在该分支追加的宏（`grep -nE "CFLAGS ?\+=" Makefile`）；④ Conan 依赖图（若需注入 `-I/-L`） |
| 输出 | ① make 变量 `UNAME=<上游 Linux 类系统名>`；②（必要时）重述上游标志与分支宏的命令行 `CFLAGS`/`LDFLAGS`；③（回退路径）一个最小平台分支补丁 |
| 不适用 | 带 configure/CMake/meson 的项目；平台判定发生在源码内而非 make 层且无对应 make 变量可覆盖的情形（改走回退补丁） |

## 实测证据（xcwd 0-2.gbpe2c777c，OHOS PC aarch64）

| 项 | 结果 |
|---|---|
| 上游 | https://github.com/schischi/xcwd commit `e2c777cbf3a226522a4871f97916f0cb0bee3688`；`Makefile` 22 行、`xcwd.c` 单文件 |
| 未覆盖时 | `make CC=clang` → `Makefile:20: *** Operating System not supported..  Stop.`（解析期终止，无编译行） |
| 应用方案后 | `make UNAME=Linux CC=clang CFLAGS="… -DLINUX -I<libx11> -I<xorgproto>" LDFLAGS="-L<libx11> -lX11"` → clang 15.0.4（`aarch64-unknown-linux-ohos`）编译链接成功 |
| 产物校验 | `readelf -h`：ELF64 / `EM_AARCH64` / `ET_DYN`(PIE)；`readelf -d`：`NEEDED = libX11.so.6, libc.so`，无 `RPATH/RUNPATH` |
| 平台分支确已编入 | 二进制内存在仅属 `#ifdef LINUX` 的字面量 `/proc/%ld/cwd`、`/proc/[0-9]*`、`/stat`（`xcwd.c:235/161/172`） |
| 运行期 | 无 `DISPLAY`：exit 1、无输出（上游 `xcwd.c:69-71`）；剥离 Conan 库路径：加载器失败 exit 127（`Error loading shared library libX11.so.6`） |
| 门禁 | 干净 `conan create` rc=0（消费者 13/13 断言）；W3 本地 CI L0–L5 1/1；W4 独立审计 verdict=pass |
| 补丁数 | **0**（`patches: {}`，源码与 Makefile 与上游逐字节一致） |

## 与既有知识的关系

- `similar_to: E14411` —— 命令行 make 变量覆盖 Makefile 内定义的宏（本条陷阱 #2 的机制来源；本条把它扩展为"平台分支宏被丢弃"的判据）。
- `similar_to: E007` —— config.guess 不识别 HarmonyOS 的 Autotools 版本；**本模式是它的手写 Makefile 对应面**，两者不可互相套用。

## 参考实现

- `archives/x/xcwd/0-2.gbpe2c777c/conanfile.py`（`build()` 与 `_dependency_flags()`）
- `archives/x/xcwd/0-2.gbpe2c777c/test_package/test_xcwd.py`（HC-3 断言平台分支字面量确已编入 —— 可用于验证本方案没有落进"禁止做法 #2"）
