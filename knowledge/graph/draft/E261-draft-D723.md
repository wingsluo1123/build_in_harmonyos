# E261 — /usr/bin/expr 对 BRE 交替模式 `\|` 返回垃圾字节 (config.status 计算 ac_dir 出错)

## 错误特征

- 子目录 Makefile（如 ncurses/Makefile、progs/Makefile）中 `top_srcdir`/`srcdir`/`prefix` 等变量行出现随机高字节乱码（含 `kk` 模式，如 `/\x97\x1b\x9b\x89\x12+kk...`），每次运行结果不同
- `make` 报 `Makefile:NN: *** missing separator. Stop.`
- 链接阶段报 `undefined symbol`（因生成的 .c/.o 缺失）
- `expr` 直接测试交替模式返回垃圾：`expr X"a/b" : 'p1' \| X"a/b" : 'p2'`

## 触发条件

- 构建系统: autotools（configure + config.status）
- 阶段: configuration（config.status 生成子目录 Makefile 时）
- 平台: HarmonyOS PC（HMDFS），`/usr/bin/expr` 为受限实现

## 根因分析

autoconf 生成的 config.status 用 `expr X"$ac_file" : 'X\(.*[^/]\)...' \| ... \| . : '\(.\)'` 计算 `ac_dir`（含 BRE 交替 `\|` 模式）。HarmonyOS 平台上 `/usr/bin/expr` 对 `\|` 交替模式处理存在 bug，返回垃圾字节（非确定性，每次不同）。`ac_dir` 变垃圾 → `ac_dots`/`ac_top_srcdir` 变垃圾 → 子目录 Makefile 的 `top_srcdir`/`srcdir`/`prefix` 等变量行被写坏。顶层 Makefile 不受影响（其 ac_dir 计算路径不同或值较短恰好未触发）。

## 解决方案

### 推荐方案

configure 中把 `as_expr="expr"` 改为 `as_expr="false"`，强制 config.status 走 `echo X"$ac_file" | sed ...` fallback 计算 ac_dir：

```bash
sed -i 's/^  as_expr="expr"/  as_expr="false"/' configure
```

（config.status 由 configure 生成，修补 configure 后生成的 config.status 自动继承。）

### 禁止做法

- ❌ 不要手工修复生成后的 Makefile（每次 config.status 重跑会再次写坏，且被改文件非源码）
- ❌ 不要用 --build/--host 硬编码绕过（治标不治本，且触发交叉编译判断）

## 验证

```bash
# 1) 确认 expr 有 bug
expr X'a/b' : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| expr X'a/b' : 'X\(/\)' 2>&1 | cat -v
#    （若输出含高字节乱码 = 命中本模式）

# 2) 修补后重新 configure
sed -i 's/^  as_expr="expr"/  as_expr="false"/' configure
./configure --prefix=... ; grep '^top_srcdir' ncurses/Makefile   # 应为 '..'，无乱码
```

## 关联条目

- 相关: E011（HMDFS UID 映射/umask 077 临时目录权限，与本条目常并发出现）
- 相关: E052/E060/E110/E112（HMDFS config.status 临时目录问题）
- 相关: E160（config.guess 识别 HarmonyOS）
