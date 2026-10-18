# E553 — clang/GCC>=10 默认 -fno-common：重复暂定定义变成 duplicate symbol

## 错误特征

```
ld.lld: error: duplicate symbol: lcd_bck_info
>>> defined at sysfs_backlight.c
>>> defined at mactel/x1600_backlight.c
>>> defined at mactel/nv8600mgt_backlight.c
```

或 GNU ld：`multiple definition of 'lcd_bck_info'`。

## 触发条件

- 构建系统: 任意（老 C 项目）
- 阶段: linking
- 编译器: clang ≥ 11 / GCC ≥ 10（默认 `-fno-common`）

## 根因分析

在 GCC<10（及老 clang 的默认）下，文件作用域的 `int x;`（无初始化）是
**暂定定义**，被放进 COMMON 段；多个编译单元各自写 `int x;` 会被合并成同一符号。
GCC 10 / clang 11 起默认 `-fno-common`，同样代码会生成多个强定义 →
链接期 `duplicate symbol`。这类代码常见于 2011 年前的 C 项目
（把变量定义写在了多处，或通过内部头文件被多个 TU 包含）。

## 解决方案

### 推荐方案

加 `-fcommon` 恢复旧语义（本仓库既有惯例）。对纯 C 老项目最省事，
不改源码、不引入行为变化：

```bash
make -j1 CPPFLAGS="-fcommon"
```

### 备选方案

保留一处定义，其余处改为 `extern` 声明（或全项目改为单一定义 + 头文件 `extern`）。
改动面大，仅在 `-fcommon` 引发其他问题时使用。

### 禁止做法

- ❌ 把"重复"定义 `static` 化或注释掉——改变符号可见性，其他编译单元看不到该变量，运行时各模块数据不同步。
- ❌ `-Wl,--allow-multiple-definition`——让链接器随意选一个定义，语义不确定。

## 验证

```bash
nm <dep>.a | grep ' C '                 # 旧语义下应为 COMMON 符号
grep -rn '^[A-Za-z_].* lcd_bck_info;' <src>   # 确认多处文件作用域定义
make -j1 CPPFLAGS="-fcommon"            # 链接应通过
```

## 关联条目

- 相关: E554（链接期问题）
