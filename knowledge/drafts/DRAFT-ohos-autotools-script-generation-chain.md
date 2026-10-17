# DRAFT — OHOS 沙箱上 autotools「脚本/文档生成链」四连坑统一适配模式

> 拟提升编号：E556（最终编号由知识库主编确认）
> 来源：xdg-utils 1.2.1 适配（2026-10-14，鸿蒙 PC 真机）
> 关联：Issue #4007 / PR !15728

## 错误特征

四个互相独立、但总在同一类包上连锁出现的报错：

```
# 1) config.status 被 /usr/bin/awk 坏符号链接绊倒（E060 tmpfs 方案解决不了这层）
./config.status: line 586: ./confDBaobJ/subs1.awk: Permission denied
config.status: error: could not setup config files machinery

# 2) 并行 make 下 %: %.in %.txt 生成链 sed 自读自写死循环（单文件膨胀 ~35GB）
make[2]: Entering directory '.../scripts'   # sed 进程数 ≈ make -j 并行度，文件持续增长

# 3) xmlto 联网拉 docbook DTD，沙箱不可达
failed to load external entity ".../docbookx.dtd"

# 4) make install 走上游 install-sh，新建脚本被 MAC 拒绝执行
/bin/sh: .././install-sh: can't execute: Permission denied
```

## 根因分析（四个独立机制）

1. **`/usr/bin/awk` 是指向 toybox 的坏符号链接**（exec 被拒）。configure 把它缓存进
   config.status 的 `$AWK`，随后 subs1.awk 处理直接 `Permission denied`。
   E060 的 tmpfs 方案只解决 HMDFS 临时目录问题，解决不了这一层。
2. **生成链并行不安全**：上游 `%: %.in %.txt` 规则是
   `awk | sed > $@` 与 `sh ./$@ --help | grep | sed -e '$d' >> $@.txt` 的管道链。
   并行 make（-jN）下 sed 进入自读自写循环，KB 级脚本文件膨胀至 ~35GB
   （xdg-utils 2026-10-14 实证：10 个 sed 并行，合计 ~350GB）。
3. **xmlto 需联网**：scripts/Makefile 的 all 目标含 html/man，xmlto 联网拉
   docbookx.dtd 在沙箱不可达。
4. **install-sh 触发 MAC**：其复制新建的可执行文件触发 hishell_hap
   "can't execute: Permission denied"（与 G17 同源）。

## 解决方案（统一配方模式）

```sh
# (a) 源码复制到 tmpfs 构建，规避 HMDFS umask 077 临时目录问题（E060；acpid/2.0.34 先例）
cp -a $SRC /data/storage/el2/base/build && cd /data/storage/el2/base/build

# (b) 显式钉定 GNU awk + PATH 前置 hnp bin，覆盖 /usr/bin/awk 坏符号链接
./configure AWK=/data/service/hnp/bin/awk PATH=/data/service/hnp/bin:$PATH ...

# (c) 强制串行：此类生成链并行不安全（真机 --parallel 8 经验不适用于脚本生成链）
make -j1

# (d) 文档工具用离线桩：work 根放 xmlto 桩脚本（case 分支覆盖 man/html/
#     html-nochunks/txt 等上游实际调用的全部 mode），桩目录前置 PATH；
#     桩必须为每个 mode 真实产出目标文件，否则 make 反复重跑该规则（正是
#     sed 循环的放大器）
# (e) 跳过 make install，用 Python shutil.copy2 复制构建产物（保留执行位），
#     规避 install-sh 新建文件 MAC 拒绝；CMake 包无需此步
```

## 验证

```bash
# 命中判定：Makefile 出现 %: %.in、xmlto/asciidoc/pod2man、install-sh 即为该类包
grep -l '%: %.in' Makefile.am scripts/Makefile.am 2>/dev/null
grep -E 'xmlto|asciidoc|pod2man' scripts/Makefile.am
# OBS 观测：sed 进程数 ≈ make -j 并行度且目标文件持续增长 = 命中坑 2

# xdg-utils 1.2.1 实证：xdg-* 13 个脚本全部生成，
# test_package 真实执行 xdg-open --version / xdg-mime --help 通过（非 print("ok")）
```

## 推广价值

覆盖所有含**脚本/文档生成链**的 autotools 包（Makefile 出现 `%: %.in`、
xmlto/asciidoc/pod2man、install-sh）。四个坑各自都能在别的包上复现，
且 E060 tmpfs 单独使用对该类包无效——必须四件套一起上。