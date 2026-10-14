# 4ti2 1.6.10.1 Adaptation Notes

> 本版本相对 1.6.10 的唯一功能性变化：依赖由 `gmp/6.3.0`（仅 C API）切换为
> `gmp/6.3.0.1`（以 `--enable-cxx` 构建，提供 `gmpxx.h` 与 `libgmpxx.so`），
> 从而启用 4ti2 的**任意精度（arbitrary-precision）后端**：`lib4ti2gmp.a`
> 静态库与 `4ti2gmp` 可执行文件被构建并打包，`walk -p arb` 4 个 CLI 用例与
> 2 个 `test_input_conversion_*` API 测试由失败/未构建转为通过。

## 1. 构建配置

| 项 | 值 |
|----|----|
| 上游版本 | 4ti2 1.6.10（官方 tarball，版本号后缀 .1 属 R37 适配修复） |
| 源码 | https://github.com/4ti2/4ti2/releases/download/Release_1_6_10/4ti2-1.6.10.tar.gz |
| sha256 | f7c191beb14246b643e4fd5b18b53d9966693b9e6d3a569441a0e3ca14b1a86b |
| 构建系统 | Autotools（configure + make，libtool） |
| 包类型 | library，默认 `shared=False` → `--enable-static --disable-shared` |
| 依赖 | glpk/5.0（shared）、gmp/6.3.0.1（shared，force 统一，见 §3） |
| 编译器 | clang 15 / clang++ 15（profile `~/.conan2/profiles/ohos-aarch64`） |
| 平台 | OHOS 6.0 / armv8（aarch64），真机本地编译 |

configure 关键参数：`--prefix`（toolchain 注入）、`--with-gmp=<gmp_pkg>`、
`--with-glpk=<glpk_pkg>`、OHOS 下追加 `--build=aarch64-unknown-linux-musl
--host=aarch64-unknown-linux-musl`。

## 2. OHOS 适配点（全部在 build() 内联完成，无 patches/*.patch）

1. **config.guess 不识别 OHOS**：显式传
   `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`。
2. **config.status 的 mktemp -d 在 OHOS/SELinux 失败**：tarball 内 configure
   使用 `` tmp=`(umask 077 && mktemp -d "./confXXXXXX") ... ` ``，在本机产生
   setgid 但无组执行位的目录。build() 内将该片段精确替换为
   `tmp="./conf$$-$RANDOM"; (mkdir "$tmp" 2>/dev/null); test -d "$tmp"`；
   模式未命中时 `self.output.warning(...)` 显式告警（不静默）。
   为何不保留上游 `umask 077`（AI 检视第 7 项的实测回复）：在 HMDFS 上
   `(umask 077 && mkdir)` 产生的是 setgid `drwx--S---` 目录，随后向其中创建/
   执行文件一律 `Permission denied`（最小复现：该目录内写 subs1.awk 即失败），
   config.status 正是靠该目录里的 awk 工作，故 077 会直接令 configure 失败
   （实测报 `./conf.../subs1.awk: Permission denied`）。该临时目录位于隔离的
   构建文件夹内、归构建用户所有、构建结束即随树删除，多用户竞争风险在本环境
   不成立，因此 mkdir 不加 077 是平台约束下的正确形态。
3. **测试脚本 shebang 为 /bin/bash**：本机 bash 在 `/data/service/hnp/bin/bash`。
   configure 由 `test/*.in` 模板生成可执行脚本，故在 configure **之前**内联
   修补模板（`check.template.in`、`subdirsum.in`、`flavorsum.in`、
   `reportfailures.in`、`ppi/check-ppi.in`）的 `#!/bin/bash` / `#! /bin/bash`。
4. **CONFIG_SHELL**：build() 内设 `CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash`。
5. **依赖注入（CPPFLAGS/LDFLAGS）**：
   `CPPFLAGS="-I<gmp>/include -I<glpk>/include"`；
   `LDFLAGS="-L<gmp>/lib -L<glpk>/lib -Wl,-rpath,<gmp>/lib -Wl,-rpath,<glpk>/lib"`；
   `LD_LIBRARY_PATH=<gmp>/lib:<glpk>/lib`。两个依赖均为 shared，故两个 lib
   目录都注入 rpath，保证 `4ti2gmp`（链接 `-lgmpxx -lgmp`）等工具直接可运行。

**R6/R8 说明**：以上修改均不使用 patches 管线——configure 与 `*.in` 是
tarball 内生成文件，精确字符串替换 + 未命中告警比静态补丁易维护，且 shebang
依赖本机设备路径，写进补丁会把绝对路径固化。配方与内联修改**均未引入
`__OHOS__` 宏**（PF5 无风险），也**未裸用 `${CC}`/`${CFLAGS}` 等未定义 shell
变量**（编译器/标志全部来自 Conan Toolchain，R33）。

## 3. 依赖版本冲突的处理（force=True）

`glpk/5.0` 配方声明 `requires("gmp/6.3.0")`，与本包所需 `gmp/6.3.0.1` 冲突。
处理为 `self.requires("gmp/6.3.0.1", force=True)` 统一依赖图。安全性经实测论证：

- 制品仓 glpk 二进制 `libglpk.so` 的动态依赖 `NEEDED` **只有 libc.so**，
  **不含 libgmp**（`nm -D` 中无任何 `__gmp*` 未定义符号——该 GLPK 构建实际
  未使用 GMP），因此运行期不依赖具体 gmp 版本；
- gmp 6.3.0 与 6.3.0.1 的 SONAME 同为 `libgmp.so.10`（补丁级版本，ABI 兼容）。

`force` 会改变 glpk 的 package_id（其 require 的 gmp recipe 进入哈希），由
制品仓预编译件对应的 `e046a7f3...` 变为本图下的 `5da9c4c6...`，该新 id 在
制品仓与本机均无二进制。为遵守"禁止重编依赖、使用制品仓预编译件"，采用 Conan
原生命令将**同一个已发布 glpk 二进制**重新登记到新 id 下：`conan cache save`
导出 → 修改 `pkglist.json` 的 package_id → `conan cache restore`。二进制内容
逐字节不变，仅缓存索引中的 id 不同，无任何重编译。

## 4. 上游测试清点（R51 第一步：目录级，全部可核对）

- **物理 `.chk` 文件 = 185 个**（`find test -name '*.chk' | wc -l` = 185）。
- 这些 `.chk` 由 23 个测试目录承载，经各目录 Makefile 中的
  **30 次 `check.template` 调用**（flavor：默认 + gmp 子目录）展开为
  **253 次 check.template 工具调用**；另 `test/ppi` 用 `check-ppi.in`
  产生 **3 次 ppi 调用**（ppi5/ppi10/ppi16）。CLI 工具调用合计 **256 次**。
- **API 测试程序 = 6 个**：
  - `test/qsolve/api/`：`qsolve_main`、`rays_main`、`circuits_main`（3 者注册
    于 automake `TESTS`），另 `test_input_conversion_64_to_gmp`、
    `test_input_conversion_gmp_to_64`（注册于 `check_PROGRAMS` 但上游刻意**不**
    放入 `TESTS`，由随附 `.sh` 包装脚本驱动）；
  - `test/zsolve/api/test_zsolve_api`（注册于 `TESTS`）。

### 逐目录 CLI 调用数（按 check.template 实际 FILES 枚举，非估算）

| 目录 (flavor) | 调用数 | | 目录 (flavor) | 调用数 |
|---|---|---|---|---|
| gensymm | 1 | | qsolve/gmp (arb) | 3 |
| ppi (check-ppi) | 3 | | qsolve (-maxcutoff) | 13 |
| output/binomials | 1 | | qsolve (-maxinter) | 13 |
| output/maple | 1 | | rays (-m) | 11 |
| output/positive | 1 | | rays (-s) | 11 |
| genmodel | 4 | | walk (-32) | 4 |
| circuits (-m) | 6 | | walk (-arb) | 4 |
| circuits (-s) | 6 | | zbasis | 10 |
| groebner/gmp (-fifo) | 4 | | normalform | 2 |
| groebner/gmp (-weighted) | 4 | | graver | 7 |
| groebner (-fifo) | 20 | | zsolve | 9 |
| groebner (-weighted) | 20 | | hilbert | 8 |
| markov/saturation | 17 | | minimize | 7 |
| markov/maxmin | 4 | | markov (-hybrid) | 26 |
| markov/gmp (-hybrid) | 5 | | markov (-project-and-lift) | 26 |
| markov/gmp (-project-and-lift) | 5 | | **合计** | **256** |

## 5. 真机实测明细（R51 第二步/第三步，OHOS aarch64 真机，2026-10-04）

对最终配方 conan create 的构建树
（`~/.conan2/p/b/4ti29afe1bcf92496/b/build-release`）执行：

```
make check -k -j1
# 运行时：
#   CONFIG_SHELL=/data/service/hnp/bin/bash
#   LD_LIBRARY_PATH=<gmp/6.3.0.1>/lib:<glpk/5.0>/lib
```

| 类别 | 通过/总数 | 通过率 |
|------|-----------|--------|
| CLI check.template（30 次模板，253 FILES） | 253/253 | 100.0% |
| CLI ppi check-ppi（ppi5/10/16） | 3/3 | 100.0% |
| **CLI 工具调用合计** | **256/256** | **100.0%** |
| qsolve API：qsolve_main / rays_main / circuits_main | 3/3（automake # PASS: 3） | 100% |
| qsolve API：test_input_conversion_64_to_gmp | 1/1（.sh 包装两条命令 rc 0） | 100% |
| qsolve API：test_input_conversion_gmp_to_64 | 1/1（同上） | 100% |
| zsolve API：test_zsolve_api | 1/1（.trs PASS） | 100% |
| **API 程序合计** | **6/6** | **100.0%** |
| **总计（256 CLI + 6 API）** | **262/262** | **100.0%** |

统计方式（可复核）：日志中每个 file×flavor 由 check.template 打印且仅打印一次
`<command> ... passed`（失败为 `... FAILED`）。对 make check 日志做
`grep -oE '\.\.\. passed' | wc -l` = **256**，
`grep -oE '\.\.\. FAILED' | wc -l` = **0**；逐块按 `CHECKING:` 列表核对，
30 个 check.template 块的 FILES 数之和 = 253（无一块多/少），多出的 3 个
passed 属 `ppi/check-ppi`（无 EXECUTABLE 头）。顶层与各子目录均输出
`**** ALL TESTS PASSED! ****`；全日志 `grep -cE 'Error [0-9]+'` = 0。

### 目标转绿项（本版本核心收益）

- `walk -p arb` 4 例全部通过：
  `walk -p arb -q 344 / cuww1 / grin / prob20 ... passed`；
- `test_input_conversion_64_to_gmp` 与 `test_input_conversion_gmp_to_64`
  在 1.6.10 **无法构建**（缺 gmpxx.h），本版本**已构建并 PASS**。

### 仍失败用例

**无。** CLI 256/256、API 6/6 全部通过，不存在需说明的残留失败项。

### 测试运行器注意（踩坑记录）

- 必须用 `-j1`：`-j2` 时 jobserver 的 `mkfifo` 在 HMDFS 上报
  `Operation not permitted`，且并行子 make 产生过不完整、输出交错的运行
  （曾观察到仅 168 passed 的假象）。串行 `-j1` 结果确定、可逐块核对。

## 6. test_package 实测与断言口径

test_package 由 `test.c`（对齐上游 `test/qsolve/api/qsolve_main.cpp`，INT_64）
与 `conanfile.py` 组成。conan create 中实测输出：

- `backend artifacts verified: .../p/bin/4ti2gmp, .../p/lib/lib4ti2gmp.a`；
- `4ti2gmp --version` → 打印 `4ti2 version 1.6.10`（真实加载 libgmpxx/libgmp）；
- `./test_probe` → `4ti2 qsolve C API test: PASSED (4x3 qhom matrix verified, 12 entries)`；
- `gensymm 3 3 3 1 333`（在 $TMPDIR 草稿目录运行）正常退出。

链接行（按链接器实际报错确定，非预设）：首次尝试缺 `-l4ti2gmp -lgmpxx` 时
`ld.lld` 报 `undefined symbol: operator<<(std::ostream&, __mpz_struct const*)`，
该符号在 `lib4ti2gmp.a`、并依赖 `libgmpxx`；最终链接行为

```
clang++ test.o -o test_probe <-L/-rpath-link ...> \
  -l4ti2int64 -l4ti2gmp -l4ti2common -l4ti2util -lgmpxx -lgmp -lglpk -lm
```

**assertion_count = 24**，口径（全部真机实测，无占位符）：

| 来源 | 断言数 |
|------|-------|
| test.c 结构性失败分支（create_state NULL、create mat/rel/sign、compute、get qhom NULL、rows、cols） | 8 |
| test.c 矩阵元素逐一比较（4×3） | 12 |
| 任意精度后端产物存在性（bin/4ti2gmp、lib/lib4ti2gmp.a，缺失即 AssertionError） | 2 |
| 4ti2gmp --version 真实执行 | 1 |
| gensymm CLI 执行 | 1 |
| **合计** | **24** |

test_package 实质依赖被测包（R34）：`test_probe` 真实调用 qsolve C API 并链接
4ti2 静态库，test() 真实执行包内二进制；移走 include/lib/bin 后必失败。

## 7. 与 1.6.10 的差异

| 维度 | 1.6.10 | 1.6.10.1 |
|------|--------|----------|
| GMP 依赖 | gmp/6.3.0（仅 C API，无 gmpxx.h） | gmp/6.3.0.1（--enable-cxx，shared） |
| HAVE_GMP_WITH_CXX | 未定义 | 定义 |
| lib4ti2gmp.a | 不构建 | **构建并打包** |
| 4ti2gmp 可执行文件 | 不构建 | **构建并打包**（bin，19 个工具） |
| gmp 测试子目录（groebner/markov/qsolve） | 不进入 | 进入，+21 次 CLI 调用 |
| CLI 实测 | 231/235（98.3%，walk arb 4 例运行失败） | **256/256（100%）** |
| input_conversion API（2 个） | 无法构建 | **构建并 PASS** |
| API 实测 | 4/4 | **6/6** |
| conanfile 其余逻辑 | — | 完全保留（triplet/mktemp/shebang/CONFIG_SHELL/注入） |

CLI 调用数 235 → 256 的 +21 严格对应三个 `if HAVE_GMP_WITH_CXX` 控制的子目录：
groebner/gmp 8（4+4）、markov/gmp 10（5+5）、qsolve/gmp 3；235 为 C++ 后端
不可用时的基线（walk -arb 为无条件行，1.6.10 时执行但运行期失败）。

## 8. Test Results 汇总

- conan create（最终配方，recipe f728d06c4d173896fa5487d892ff9b49）：**PASS**，
  Package `30231a5a...` created，test_package **PASS**（assertion_count 24）。
- 上游 make check（真机）：CLI **256/256** + API **6/6**，总 **262/262 = 100%**，
  无失败项。
---

**编译结束**: 2026-10-04
**最终状态**: built
