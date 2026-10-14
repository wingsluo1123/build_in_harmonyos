# 消费者 CLI 测试的三种"空跑假绿"

> Draft 知识条目（待人工/AI 审核后方可 promote 为正式 E 条目）
> 来源：xpdf 4.06 配方起草，2026-10-01，commit `cb773caaa`
> 修订：2026-10-09，形态③由 AI 检视抓出（PR #15012 comment `192726392`，disc `f43c32aa…`）
> 对应 kv：`DRAFT-xpdf-cli-vacuous-success-and-wrong-flag.kv`

## 一句话

用安装后的 CLI 产物做消费者 roundtrip 时，**"退出码 0"不等于"做了功"**，
**照抄同族工具的旗标会静默失效**，而**"文件存在"可能只是自己重定向造出来的**——
三者任一都足以得到一条全绿的假测试。

## 触发条件

- test_package 驱动安装后的 CLI 二进制做功能 roundtrip（PF3/L0c 语境）
- 尤其是 PDF/媒体类工具集：pdftotext / pdfimages / pdftoppm 等
- 写测试时参考了"同族工具"的经验（如把 poppler 的用法搬到 xpdf）
- 断言写成 `> "$OUT"` 之后再 `[ -f "$OUT" ]`（shell 先建文件后跑命令）

## 实测到的三种形态（xpdf 4.06）

### ① 旗标不存在 → 打印 usage 并以非零退出，`|| true` 会把它吞掉

```
$ pdfimages -png sample.pdf out
pdfimages version 4.06 [www.xpdfreader.com]
Copyright 1996-2025 Glyph & Cog, LLC
Usage: pdfimages [options] <PDF-file> <image-root>
  -f <int>   : first page to convert
  ...
$ echo $?
99
```

xpdf 的 `pdfimages` **没有 `-png`**（那是 poppler 的选项），默认写 **PPM**。
若测试写成 `pdfimages -png ... 2>/dev/null || true` 再断言产出，
非零退出被 `|| true` 吞掉，测试继续往下跑，最终只在一个"文件不存在"的
FAIL 上暴雷；更糟的写法是只断言退出码，那就直接判绿了。

### ② 无可提取对象 → rc=0 但零产出文件

```
$ pdfimages sample.pdf out        # sample.pdf 内无任何图像 XObject
$ echo $?
0
$ ls out*
ls: out*: No such file or directory
```

**成功退出的空跑**。这类行为对提取类 CLI 是设计使然（没有可处理的东西就不报错），
但在退出码上与"真的处理了"完全不可区分。

### ③ 重定向先建文件 → `[ -f "$OUT" ]` 断言恒真

```sh
$PDFDETACH -list "$PDF" >"$WORK/detach.txt" 2>/dev/null || true
if [ -f "$WORK/detach.txt" ]; then ok "produced a report"; fi   # ← 恒真
```

POSIX shell 在执行命令**之前**就打开重定向目标（`O_WRONLY|O_CREAT|O_TRUNC`），
所以文件总是存在——与命令是否成功、甚至是否安装都无关。实测对照（同一台宿主，
PATH 里去掉 pdfdetach 之后）：

| 断言写法 | 结果 |
|---|---|
| 旧：`[ -f "$WORK/detach.txt" ]` | **15/15 PASS，rc=0**（工具 rc=127 也绿） |
| 新：`-n "$PDFDETACH"` 守卫 + stdout/stderr 分流 + `-s` + grep 确定串 | **14/17，3 项 FAIL，rc=1** |

同族的隐患：`2>/dev/null` 还会把 "command not found" 一起吞掉，于是失败连痕迹都不留。
修法要点：stdout 单独落盘（stderr 另存，别合流也别丢弃）、先判工具非空、
再断言**非空**且**含上游确定串**——本例取 `pdfdetach.cc:146-148` 的
`<n> embedded files` 与 `N: <name>`。夹具也应内嵌真实附件（`/Names /EmbeddedFiles`）
否则只能断言到 `0 embedded files`，看不到 detach 能力本身。

## 正确做法

1. **旗标以该二进制 `-h` 实读为准**，不照搬同族工具：
   ```sh
   pdfimages -h 2>&1 | head -20
   ```
2. **夹具必须内嵌真实对象**，让工具有活可干。本例的夹具生成器现算一个 PDF，
   内嵌 2x2 DeviceRGB / FlateDecode 图像 XObject（`gen_fixture.py`）。
3. **断言落在产物内容上**，而不是"有文件"或退出码：
   ```sh
   head -3 "$IMG" | grep -q '^P6'                      # 二进制 PPM 头
   head -2 "$IMG" | tail -1 | grep -qE '^2[[:space:]]+2$'   # 尺寸等于夹具声明
   [ "$(wc -c < "$IMG")" -gt 16 ]                        # 像素载荷非空
   ```
4. **`-listonly` 这类"不需要输出根"的子命令**也要用对（本例 `-list` 需要 root，
   `-listonly` 不需要），实读 usage 确认。
5. **重定向目标不能当断言对象**：`> "$OUT"` 先创建文件，`[ -f "$OUT" ]` 恒真。
   stdout/stderr 分流落盘，先判工具非空，再 `-s` + `grep` 上游确定串。

## 效果

改夹具 + 改旗标后，消费者测试从 **10/12（2 项 FAIL）** 变为 **15/15 通过**
（Mac 侧真实 xpdf 4.06 构建产物实跑）。若不改，这两项要么假绿、要么在 CI 上
表现为与配方无关的莫名失败。

形态③修复（2026-10-09）后，夹具再内嵌一个真实附件，断言从 15 项增至 **17 项**：
宿主真实 4.06 构建 **17/17**，OHOS aarch64 真机 CI 同源脚本 **17/17**、
`BUILD_AND_TEST_RC=0`；同一环境下旧写法仍 15/15 假绿——差异即本条的价值。

## 与既有条目的关系

`DRAFT-E650`（meson test 无参条目空跑假绿）是**同一原则的不同形态**：
E650 是"测试框架注册了不带参数的条目"，本条是"CLI 自身在无输入时设计性空跑"
+"旗标不存在被静默吞掉"。两者都不能靠退出码区分真假绿。

## 设备不可用时的替代校准

在宿主用同版本源码做一次构建，**仅用于校准断言口径**，
不作为交付构建、也不替代设备侧实测通过率（后者须在 MANIFEST 中明确标注待复跑）：

```sh
cmake <src> -DCMAKE_BUILD_TYPE=Release
cmake --build . --target pdftotext pdfinfo pdffonts pdfimages pdfdetach
PATH=<build>/xpdf:$PATH sh test_package/test_xpdf.sh
```
