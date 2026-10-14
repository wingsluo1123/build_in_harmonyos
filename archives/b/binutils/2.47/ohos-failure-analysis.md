# binutils 2.47 HarmonyOS PC 未通过项分析

## 证据身份

- 上游归档 SHA256：`154ab23b60070e8f27013c22977f1129425d67d1e8acd6e13010e617811e4cff`
  （`https://ftp.gnu.org/gnu/binutils/binutils-2.47.tar.xz`，29,034,716 字节）。
- 补丁重放：2.46.0 配方 25 个补丁对 pristine 2.47 逐项重放，最终 25/25 严格通过
  （0 reject）。其中 24 个沿用原 hunk 上下文，0016 因 2.47 改动 gprof 测试
  Makefile 而重新生成。
- 2.47 新增/变更的计数逐项实测（见 notes.md 表格）：ld `.exp` 187→188、
  ld 执行驱动 184→185、启用 `.exp` 379→380；libiberty demangle 用例
  860→862、PASS 行 69→73。

## 结论先行

本文件登记 **2.47 相对 2.46.0 的差异**，以及本轮本地验证的边界。2.46.0 已合入
（!9025），其 35 项 FAIL 的逐项归因见 `archives/b/binutils/2.46.0/ohos-failure-analysis.md`。
2.47 的上游测试结论 **以平台 CI 为准**，本轮不复制 2.46.0 的数字充数。

## 2.47 补丁重放差异（逐项）

唯一需要改写的补丁是 `0016-gprof-ohos-shell.patch`。

**2.46.0 的形态**：把两条 gprof 测试生成规则从直接执行脚本改为 `$(SHELL) <script>`，
并补 `LOG_COMPILER = $(SHELL)`。

**2.47 的变化**（`gprof/testsuite/Makefile.am` / `Makefile.in`）：

| 变化点 | 2.46.0 | 2.47 |
|---|---|---|
| 测试脚本数 | 2（`tst-gmon-gprof.sh`、`-l.sh`） | 3（新增 `tst-gmon-gprof-l2.sh`） |
| 规则参数 | `$(GPROF) tst-gmon$(EXEEXT)` | 追加 `$(target)` |
| `check_SCRIPTS` 来源 | 直接赋值 | 经 `am__append_1` 间接赋值 |

**2.47 的改写**：三条生成规则全部改为 `$(SHELL) $(srcdir)/...`，`LOG_COMPILER = $(SHELL)`
保留。语义与原补丁一致（HMDFS 下不直接执行脚本），且覆盖了新增的第三条脚本。

其余 24 个补丁（0001-0015、0017-0025）逐项重放通过，未改动内容。

### 关于补丁行号

`apply_conandata_patches` 使用 `patch_ng`，要求 hunk 行号与目标文件**精确匹配**
（不像 GNU patch 默认允许 fuzz）。2.47 的 `configure` 等生成文件行号相对 2.46.0 有位移，
因此所有补丁均以「pristine 2.47 ↔ 打补丁后 2.47」的真实 diff 重新生成，保证零 fuzz。

## 本地验证边界（ENV-GAP，非配方缺陷）

CI（`ci/conan/build_and_test.sh`）以 **`-pr:h=<profile> -pr:b=<同一 profile>`** 调用
`conan create`，即 build 与 host 上下文都是 OHOS，因此 `settings_build.os == "OHOS"`
成立，配方的原生测试路径（runtest 启动器、运行时 preflight、DejaGNU transport、
上游 `make check`、libiberty 复核）全部会执行。

本机（共用鸿蒙 PC）**没有 HNP 包集合**：

```text
$ stat -c 'links=%h mode=%a owner=%U' /data/service/hnp
links=2 mode=711 owner=root
$ ls /data/service/hnp/bin/llvm-objcopy
ls: /data/service/hnp/bin/llvm-objcopy: No such file or directory
$ ls /data/service/hnp
ls: /data/service/hnp: Permission denied
```

`links=2` 表示该目录没有任何子目录 ⇒ 无 `bin/` ⇒ **HNP 未安装**，是 root 拥有的空占位目录。
CI worker 上该工具链存在（由平台 provisioning 安装）。

因此配方在 `_prepare_ohos_runtime()` 处按设计快速失败：

```text
RuntimeError: OHOS test execution requires the platform tool llvm-objcopy
ERROR: binutils/2.47: Error in build() method, line 277
	shim_so = self._prepare_ohos_runtime()
```

**这是 `pc/SETUP.md` §4.0 记录的 ENV-GAP 类别，不是配方问题。** 该 preflight 的存在
是必要的：它保证「GNU ld 产物必须经平台签名后才能执行」这条约束不被静默降级。
**不得为了让本机跑绿而削弱该检查**——削弱它会让未签名产物被执行，正是该检查要防的事。

### 本机已验证通过的部分（真实证据）

`outputs/pc-validate/binutils-2.47-r2-20261010-154016/build.log`：

| 阶段 | 结果 |
|---|---|
| 依赖图（dejagnu/expect/tcl/zlib） | 全部解析成功 |
| 25 个补丁应用 | **25/25 全部 Apply patch (portability)** |
| 原生 runtest 启动器编译 | 成功 |
| runtest 启动器执行 | `DejaGnu version 1.6.3 / Expect version 5.45.4 / Tcl version 8.6` |
| 运行时 preflight | 停止于 HNP 工具缺失（ENV-GAP） |

即：**配方逻辑、补丁链、原生 shell/解释器路径、DejaGNU 工具链均已在本机实证可用**；
剩余阻塞纯粹是本机缺少 CI 才有的 HNP 工具链。

## 说明

- 上游测试通过率、libiberty 计数与消费者结果以平台 CI 日志为准；本文件不预填数字。
- 2.46.0 的 35 项 FAIL 归因继续有效（同一批用例、同一 OHOS 运行时差异），但 2.47 的
  最终 FAIL 清单需以 CI 实际输出为准，逐项比对后再登记。
