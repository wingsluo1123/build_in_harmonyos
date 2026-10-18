# lddtreepax 1.3.9 适配笔记

## 包定性

- `lddtreepax` 不是独立上游库：它是 **gentoo/pax-utils** 项目（tag `v1.3.9`）内的
  子包——python 实现的 `lddtree`（`lddtree.py`），Alpine 打包时由 `lddtree` 重命名
  而来（APKBUILD：`subpackages="... lddtreepax:_lddtreepax:noarch"`，
  `_lddtreepax() { depends="python3 py3-elftools"; amove usr/bin/lddtreepax }`）。
- 本包交付物 = `lddtree.py` 单文件（安装为 `bin/lddtreepax`，0755）+ COPYING。
  同源的 C 工具（scanelf/dumpelf/pspax/scanmacho）属于 pax-utils 子包，已由
  `pax-utils/1.3.10` 独立适配并发布（本包不含其源码，符合"只处理目标库自身文件"）。

## 上游坐标

- tag archive 即官方制品（无独立 release 附件；GitHub release 页 404、tarball 无
  CHANGELOG/NEWS → **发布说明无法核验**，依赖证据以下游构建文件为准）。
- codeload 端点实测 148310 B，sha256 `d8db28f8f55d03b1f302b719857e9ffd6574ecade0c3b762ebd1c215e0a68754`（2026-10-13）。
- `lddtree.py`：python≥3.8；`from elftools...`（必需，无 try/except）；
  `import argcomplete`（可选，try/except 降级）；shebang `#!/usr/bin/env python`。

## W0 依赖核验（2026-10-13，conan download --only-recipe）

| 依赖 | 版本 | 类型 | ohpcd 状态（rc） |
|---|---|---|---|
| pyelftools | 0.33 | 运行时（python 模块，必需） | 可消费 rc=0（rev 3075bf33，2026-10-12 发布；本地 OHOS 二进制 6b129b06 在缓存） |
| python3 | 3.12.9（设备解释器） | 运行时（解释器） | ohpcd 有 python/3.12.9(.1) rc=0；本配方按设备 PATH 提供（同 pax-utils/1.3.10、pyelftools/0.33 先例） |
| meson/ninja/pkgconf | — | — | 本包无编译（脚本工具），不需要 |
| libcap | 2.78 | 可选（仅 pspax 等 C 工具链接） | 可消费 rc=0；本包不涉及 |
| argcomplete | — | 可选（try/except） | ohpcd 无（0 条）；不阻塞 |
| xmlto | — | 可选（man 页） | ohpcd 无（0 条）；本包不建 man 页 |

日志：`_analysis/lddtreepax-1.3.9/12-w0-reprobes-20261013.log`、`13-pyelftools-final.log`。
无 R36 阻塞。

## R51 上游测试申报表

**清点**（pax-utils v1.3.9 源码树 `tests/`，meson 注册）：4 个目录共 **6 条**注册用例——
`tests/lddtree/meson.build` foreach sh/py/cmp → `lddtree-sh`/`lddtree-py`/`lddtree-cmp`；
`tests/pspax` → `pspax-test`；`tests/scanelf` → `scanelf-test`；`tests/source` → `source tests`。

**本包适用范围**：lddtreepax = python 实现 → 适用入口 **1 条：`lddtree-py`**
（`dotest-py` → `dotest-sfx`：`lddtree.py /bin/bash | grep -i 'none'`，负向断言，
testit 语义：smoke 文件为空才 PASS）。`lddtree-sh`/`lddtree-cmp` 依赖 `lddtree.sh` +
`scanelf`（C 工具，另一子包）→ 超出本包范围，由 `pax-utils/1.3.10` 包覆盖
（其 6 条全矩阵已在 1.3.10 notes 如实申报）。

**运行**（本机 aarch64 OHOS，2026-10-13）：

| 运行 | 命令/环境 | 结果 | 定性 |
|---|---|---|---|
| 原样执行（未打补丁，meson test 等价环境） | `builddir=… srcdir=… current_srcdir=… bash ./dotest-py` | `PASS: lddtree.py.smoke` RC=0 | **空跑**（E363 形态）：`env: exec python: No such file or directory`（设备无裸 python）+ fixture `/bin/bash` 不存在，空 stdout 满足负向断言。日志 `_analysis/lddtreepax-1.3.9/16-dotest-py-raw.log` |
| 配方态执行（conan create build() 内） | 补丁后 shebang + pyelftools VirtualRunenv + meson test 等价三环境变量 | RC=0（预期同上空跑） | 空跑，边界同下 |
| 修复等价探针（非上游原样） | `PYTHONPATH=pyelftools python3 lddtree.py /bin/sh \| grep -i none` | **FAIL**：smoke=`libc.so => None` | 上游负向断言在 musl 不成立（见下）。日志 `_analysis/lddtreepax-1.3.9/17-dotest-py-adapted-equivalent.log` |
| 功能探针 | `PYTHONPATH=pyelftools python3 lddtree.py /bin/sh` | RC=0，真实树输出 2 行 | 工具本身可用。日志 `_analysis/lddtreepax-1.3.9/15-lddtree-functional-probe.log` |

**musl 负向断言不成立的根因**（具体技术原因，非"没环境"）：
`lddtree.py:644-649`：`fullpath = elf["libs"][lib]["path"]; print(f"{indent}{lib}", "=>", fullpath)`。
OHOS/musl 布局中 `/lib`、`/usr/lib` 无 `libc.so` soname 链（实测仅
`/lib/ld-musl-aarch64.so.1` 与 `/usr/lib/libcrypto.so.3`）→ `libc.so` 解析 path=None →
打印字符串 `None` → 命中 `grep -i 'none'` → 负向断言失败。该断言为 glibc 环境而写：
上游 CI 矩阵中 ubuntu（glibc）跑 tests，**alpine（musl）CI 是 `-Dtests=false`**——
musl 路径上游从未被测试过，非本适配引入的缺陷。

**回填**：上游测试 6 条，本包适用 1 条，实跑 1 条，raw 通过 1/1（空跑，边界如实申报）；
修复等价探针 FAIL 及其根因如上；真实行为由 test_package 4 条实质断言覆盖
（已安装 lddtreepax 对 `/bin/sh`：provenance + rc=0 + interpreter 行 + libc.so 行）。

## 适配点

1. `patches/0001`（portability）：`lddtree.py` shebang `#!/usr/bin/env python` →
   `#!/usr/bin/env python3`。原因：设备 PATH 只有 `python3`（裸 `python` 不存在，
   原样执行实测 `env: exec python: No such file or directory`）；`/usr/bin/env` 是真机
   toybox 软链（实测可用）。同 pax-utils/1.3.10 patches/0001 机制（E037：
   解释器缺失会被 meson 误报成"测试脚本丢失"）。只改交付文件，测试脚本不改
   （build() 显式以 bash 启动）。无平台宏（R8 合规）。

2. `package_info()` 显式声明 PYTHONPATH runenv：pyelftools（package_type=
   python-require）的二进制在嵌套安装时被 skip，其 PYTHONPATH runenv 不聚合进
   消费者环境（2026-10-13 实测：`conan install --requires=pyelftools/0.33` 的
   conanrunenv 含 PYTHONPATH，而 lddtreepax→pyelftools 嵌套图的 conanrunenv
   缺失 → 消费者跑 lddtreepax 直接 ModuleNotFoundError: elftools）。本包 glob
   pyelftools 包内 `lib/pythonX.Y/site-packages` 后自行 append_path，保证已安装
   lddtreepax 开箱即用。

## 已知限制

1. musl 布局下无法解析的库在树输出中打印 `None`（如 `/bin/sh` 的 `libc.so => None`）：
   上游解析算法按 glibc soname 链设计，OHOS 无 soname 链。工具不崩溃、rc=0，
   interpreter/DT_NEEDED 结构解析正常；这是上游算法的平台边界，不属适配缺陷，
   不修改上游行为（如需修复应向上游提 issue）。
2. 上游 `lddtree-py` 用例在本平台为空跑（fixture `/bin/bash` 缺失且 `/bin` 只读
   不可补）——与 pax-utils/1.3.10 notes 同一边界；未改动任何上游测试断言。
3. `argcomplete`（可选）ohpcd 无包：try/except 降级为无 tab 补全，功能不受影响。
---

## 对话记录

### 对话 #1 (2026-10-14, 任务 1783828906105: lddtreepax 1.3.9 OHOS 适配)

- 任务：加载编译 SKILL 执行 lddtreepax/1.3.9 全流程适配（W0 依赖 → 语言预检 → 配方 → conan create → 上游测试 → conan-verify → finish）
- 关键节点：
  1. 确认目标库非独立上游：gentoo/pax-utils 的 python 实现 lddtree（Alpine noarch 子包），C 工具属 pax-utils/1.3.10 子包
  2. W0：pyelftools/0.33 可消费（conan download rc=0，rev 3075bf33dc536fd300d73d38236a0231）；无其他第三方依赖
  3. 语言预检 R47：整树（pax-utils 多工具项目）判 mixed → 收窄范围至 lddtree.py + tests/lddtree 后 python 判定通过
  4. conan create 第三次通过：前两次失败根因 = python-require 依赖 pyelftools 被 BINARY_SKIP
     （package_folder=None、runenv 不聚合）→ `requires("pyelftools/0.33", run=True)` 显式修复
  5. 上游测试 lddtree-py 实跑 1/1 raw PASS（空跑：fixture /bin/bash 缺失且 /bin 只读，E363 边界）；
     修复等价探针 FAIL 于 grep -i none（musl 无 libc.so soname 链，上游断言 glibc-only）→ 真实行为由 test_package 5 断言覆盖
  6. conan-verify：G1-G4 + L2/L4/L5 全 PASS；finish：W3 本地 CI 模拟 PASS，档案关闭 built

**编译结束**: 2026-10-14 10:43
**最终状态**: built
---

**编译结束**: 2026-10-14 13:53
**最终状态**: built
