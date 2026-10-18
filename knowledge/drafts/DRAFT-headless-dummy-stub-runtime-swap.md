# DRAFT-headless-dummy-stub-runtime-swap：无头设备上 `--without-x` 类开关只切 C 层——运行时脚本层仍在加载动态图形栈，桩派发确定性 SIGSEGV；用上游官方替代运行时层（nongraph 模式）替换 + require 链逐层二分定位

> Source: xlispstat 3.52.23 真机适配 r7–r16（HarmonyOS PC aarch64 原生 conan create，
> <真机IP>:<端口>；init.lsp → graphics → graph2.lsp:31 三级二分）
> 对应 KV: knowledge/drafts/DRAFT-headless-dummy-stub-runtime-swap.kv
> Draft only. 不修改 knowledge/graph/、doc/、索引与运维规则。

## 一句话

`--without-x`/`--disable-gui` 类 configure 开关只把 **C 编译层**切到桩实现
（dummygraph/dummycod），但**运行时脚本层**（Lisp/Python/JS 的 init/require 链）仍会
无条件加载动态图形栈并派发进桩函数——空函数体返回垃圾值 → 确定性 SIGSEGV；
正确解法是用**上游自带的替代运行时层**（本例 `nongraph.lsp`，gnuplot 绘图替代）
替换运行时层的图形 require，而不是去修桩函数。

## 错误特征（真实日志，20/20 复现）

```text
echo "(compile-file \"compiler/backquot.lsp\") (exit)" | ../../xlisp
XLISP-PLUS version 3.04
Signal 11 (core dumped)          # 不打印任何 error:，直接 SEGV
make[1]: *** [Makefile:14: compiler/backquot.fsl] Error 139
```

启动即崩（stdin 第一条输入还没读），因为崩溃发生在**启动自动加载 init 的途中**。

## 根因

1. configure 探测到无 X → `GRAPHSYS=GNUPLOT`，C 层链接 `dummygraph.c`（全部是
   `StMObPopup () {}` 这类**隐式 int 空函数**）；
2. 但 `init.lsp` 仍无条件 `(require "graphics")`；graphics.lsp 末尾
   `(require "graph2")`；graph2.lsp:31 `(send spin-proto :depth-cuing t)` 把消息
   派发进桩函数——垃圾返回值进入对象系统 → SEGV；
3. 设备无显示、无 gnuplot，该路径在本平台上**不可能有正确行为**——这不是编译问题，
   是"无头环境加载了有头运行时"的问题。

## 定位方法：require/load 链逐层二分（可复制流程）

对"启动即崩、无输出"的解释器类程序，按运行时层次三级二分，每一级都用
**"前缀文件 + 退出码"** 计数（不要用捕获输出找标记——SEGV 丢 stdio 缓冲，见查重
声明的 ulimit 草稿"陷阱"节）：

```sh
# 第一级：init 前缀二分（行数对半）
head -n $k init-orig.lsp > init.lsp
echo '(exit)' | ./interpreter >/dev/null 2>&1; rc=$?   # rc=139 即崩
# 对半收敛 → 第一条引入崩溃的行（本例：init.lsp:58 (require "graphics")）

# 第二级：对引入行加载的文件重复（本例：graphics.lsp，565 行）
# 第三级：对再 require 的文件重复（本例：graph2.lsp → 第 31 行 :depth-cuing）
```

前提纪律：
- 自动加载文件（init.lsp）插桩/替换后**必须当场恢复**，且下一个探针要先校验
  md5——恢复链一旦断一次，后续所有探针都在测污染输入（本例实测得到 0/20 崩的
  假阴性）；
- 先确认崩溃是**确定性**的（同输入 ≥10 次同结局），再二分；非确定性请先看
  栈/优化（见查重声明的 ulimit 草稿与 miscompile 条目）。

## 解法：替换运行时层（配方内幂等补丁）

```python
# conanfile.py（配方内幂等注入，非 .patch——设备 patch(1) 对模糊上下文严格匹配易 FAILED）
edits = [
    ("src/lsp/init.lsp",
     '(require "graphics")',
     '(load "nongraph") ; headless OHOS: gnuplot plotting ...'),  # 注意 Lisp 注释是 ;
    ("src/lsp/regress.lsp",
     '(require "graphics")',
     "; headless OHOS: dynamic graphics stack is not loaded"),
]
```

要点：
- `nongraph.lsp` 是**上游自带**的替代绘图层（gnuplot 后端），不是自造桩；
- 注释语法跟随目标语言（Lisp 是 `;`，写 `#` 会报 `illegal character after #`）；
- 幂等性检查要匹配替换后的标记，锚缺失时抛异常而非静默跳过。

## 交付与记录

- notes/PR 必须写明平台限制：动态图形命令（spin-plot 等）在无头设备不可用；
  替代绘图函数（plot-points/plot-lines，经 gnuplot）可用；
- 不要试图让桩"能跑"——空函数体返回垃圾是无解的，切换运行时层才是正解。

## 适用范围

- 提供 `--without-x`/`--headless`/`--disable-gui` 类开关、但运行时初始化脚本仍
  无条件加载图形栈的解释器/环境类软件（XLISP-STAT、各类 Lisp/Scheme/Smalltalk、
  带 REPL 图形层的统计/数值环境）；
- C 层以 dummy/null 桩实现图形后端、且上游附带替代运行时文件（*nongraph*、
  *no-x*、*tty* 命名）的包；
- 不适用于：有真实显示后端（broadway/framebuffer）可选的场景——那是
  E336/E527 的"显示后端替换"问题；也不适用于仅链接期 GL 符号缺失的
  header-only 库——那是 lightmapper 草稿的消费者测试问题。

## 输入 / 输出

- 输入：确定性启动 SEGV 的解释器二进制、其自动加载的 init 文件、init 的
  require/load 依赖文件清单；
- 输出：崩溃引入行（精确到文件：行号与具体派发表达式）+ 运行时层替换补丁
  （幂等、锚校验）+ 全绿构建/测试证据。

## 示例（xlispstat 3.52.23 实测）

- init.lsp:58 `(require "graphics")`（bisect：57 行前缀 10/10 过、58 行 20/20 崩）
  → graphics.lsp:565 `(require "graph2")` → graph2.lsp:31
  `(send spin-proto :depth-cuing t)`；
- 替换为 `(load "nongraph")` 后：r25 全绿——构建 ✅、上游 155/155 ✅、
  test_package 10/10 ✅、exit 0。

## 查重声明

- `E336-draft-gtk-broadway-display-backend` / E527：GTK 无显示时切换 **broadway
  显示后端**——机制是换显示层，本条是**运行时 require 链替换 + 桩派发 SEGV 二分**，
  无重合条目；
- `DRAFT-lightmapper-2.8-gl-link-stub-headless-cpu-test`：GL 桩在**链接/消费者
  测试**期的处理，不涉及运行时脚本层加载崩溃；
- `DRAFT-irsim-9.7.104-ohos-nographics-null-srcs`、`DRAFT-6380`、
  `DRAFT-ired-…-headless-l2`：分别是无图形源文件、无头断言、tty 包装，均未覆盖
  "桩派发 SIGSEGV + 官方替代运行时替换 + 三级二分法"；
- 优化敏感 SEGV（-O2 错 -O0 对）已由
  `DRAFT-ohos-silent-codegen-miscompile-byte-exact-oracle` / libstb 草稿覆盖，
  本条不重复（本例两种机制叠加时，先用本条二分到具体派发行，再按优化条目处理
  编译维度的崩因）。
