# 上游零自动化测试时的测试分母：程序级入口清点 + “只编译不执行”“交互排除”两类特殊入口

- **草稿 ID**: DRAFT-xine-0.99.14-extra-programs-upstream-denominator
- **来源**: xine-ui 0.99.14 HarmonyOS PC 适配（0 套件 → 按 10 个入口给分母，PR 审查 rule4“不得少报”口径）
- **分类**: testing / make / autotools / platform
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `make check` 在全部递归目录输出 `Nothing to be done for 'check'`（本例 20 个目录，执行用例 0）
- `grep -rln "TESTS=\|check_PROGRAMS" --include=Makefile.am .` 无命中
- `make -C src/xitk check` 之后 `session_ctrl` 并不存在（`EXTRA_PROGRAMS` 不被 `make all` 构建）
- 直接执行某些入口：`rc=159` 且**无任何输出**（SIGSYS，见 E051）
- 交互式入口 `timeout 420 xine-bugreport` → `rc=124`（一直阻塞在菜单）

## 根因

老包常见形态：release tarball 里没有测试套件，可验证行为全在**程序入口**本身。
这些入口分散在三类 automake 声明里，清点时最容易漏第二类：

| 声明 | xine-ui 实例 | 陷阱 |
|---|---|---|
| `bin_PROGRAMS` | `xine`（`src/xitk/Makefile.am:20`）、条件性 `xine-remote`（`:10`）、`fbxine`/`aaxine`/`cacaxine`/`dfbxine` | 条件变量（`$(xine_ui)`、`${fb_programs}`）使人眼漏读；`./configure` 探测失败会静默消失 |
| `EXTRA_PROGRAMS` | `session_ctrl`（`src/xitk/Makefile.am:21`）、`test`（`src/xitk/xine-toolkit/Makefile.am:17`） | **不被 `make all` 构建**，必须显式 `make -C <dir> <prog>`，否则误判“没有这个程序” |
| `bin_SCRIPTS` | `xine-check`、`xine-bugreport`（`misc/Makefile.am:38`） | 由 `.sh.in` + 构建期 perl 生成器产出，不在 `src/` 下，易漏 |

在此之上还有两类“测不了但不能不报”的入口：

1. **被平台策略终止**：`session_ctrl` 的 `connect_to_session()` 无条件调用 `setreuid()`，
   OHOS 以不可捕获的 SIGSYS 结束进程（rc=159，零输出）。可验证面只剩“OHOS 交叉编译 + 链接”这一半。
2. **交互式**：`xine-bugreport` 实测输出 2468 行后停在 `please select (1..16):`，420s 超时 rc=124，
   纳入自动化必然假红。

把“上游测试”写成 0 是套件维度的事实、却是入口维度的少报；写成“10 个全部通过”又夸大结果。
正确做法是**分母三层 + 逐个证据**。

## 最小修复方案（口径模板）

三层数字必须全文一致（`test_package/MANIFEST.yml` / `reports/test-report.md` / `notes.md` / PR 正文）：

```
上游入口（程序级清点）  = 10  = 实测 4 + 不适用 6
实测调用次数            = 9   (xine 5 + xine-check 1 + xine-bugreport 1 + session_ctrl 2)
自动化套件用例            = 0   (make check: 20 个目录 Nothing to be done)
test_package 断言        = 27   其中鸿蒙特有端到端消费者用例 = 3
```

不适用的 6 个入口必须各带**实测证据**（configure 行 / 链接探针 / 编译器错误），不能只写“环境不支持”。

配方侧把“只编译不执行”固化下来（`archives/x/xine/0.99.14/conanfile.py` 的 `build()`）：

```python
autotools.make(args=["-j1"])
# 上游 EXTRA_PROGRAMS：make all 不构建它；本平台执行会被 SIGSYS 终止（E051），故只编译校验链接
self.run("make -j1 -C src/xitk session_ctrl", env="conanbuild")
```

## 验证方法

```bash
grep -rn "bin_PROGRAMS\|noinst_PROGRAMS\|EXTRA_PROGRAMS\|bin_SCRIPTS" --include=Makefile.am .
grep -rln "TESTS=\|check_PROGRAMS" --include=Makefile.am .
make check 2>&1 | grep -c "Nothing to be done for 'check'"
make -j1 -C src/xitk session_ctrl && file -b src/xitk/session_ctrl
timeout 420 ./xine-bugreport >/dev/null 2>&1; echo rc=$?     # 124 → 交互式
```

## 验证结果

| 项 | 实测 |
|---|---|
| 零套件确认 | `grep -rln TESTS=/check_PROGRAMS` 无命中；`make check` 20 目录 Nothing to be done |
| `session_ctrl` | 构建 PASS（27008 B arm64 ELF）；执行 rc=159 SIGSYS；差分探针 `setuid(geteuid())` rc=0 存活、`setreuid(getuid(),getuid())` rc=159 |
| `xine-bugreport` | 2468 行后阻塞于 `please select (1..16):`，`timeout 420` rc=124 → 实测但不入自动化 |
| 消费者面转移 | `test_package/test.sh` 27/27（A5/B13/C5/D4），含 3 个鸿蒙特有端到端用例 |
| 门禁 | `conan create` G2 PASS；CI L1e 反向验证未被判测试空壳 |

## 禁止策略

- 禁止只报“上游 0 个测试”作为分母（少报），也禁止把不适用入口计成“已通过”（虚报）。
- 禁止为了让 `session_ctrl` 跑起来而 stub/改写 `setreuid()` 调用——违反 R40（深度适配完整性）且掩盖平台事实。
- 禁止把交互式程序塞进 `make check`/CI 自动化（必然假红或超时）。

## 相关

- 依赖条目：E051（`setreuid()` SIGSYS）、E246（seccomp SIGSYS）
- 配套草稿：DRAFT-xine-0.99.14-ac-check-readline-hard-prefix-ncursesw（其中一个“不适用入口”的具体根因）
- 口径依据：PR 审查 rule4（实测 N > 声明 N = 少报）、rule12（鸿蒙特有测试须为完整端到端消费者用例）
- 归档：`archives/x/xine/0.99.14/reports/test-report.md` §1/§2/§3
