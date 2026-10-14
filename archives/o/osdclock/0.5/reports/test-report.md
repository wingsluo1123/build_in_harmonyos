# osdclock 0.5 测试报告（HarmonyOS PC / OHOS aarch64）

## 1. 上游测试清点（R51 第一步）

osdclock 0.5（2001）**没有自动化测试套件**，逐项证据见
`test_package/MANIFEST.yml` 的 `upstream_test_audit`：

| 检查对象 | 结论 |
|----------|------|
| `Makefile` | 只有 all / osd_clock / %.o / %.o.pic / tar / install / clean 七条规则；无 `check`/`test`/`TESTS`/`check_PROGRAMS` |
| 源码树 | 无 `tests/`、`test/`、`*_test.c`、`test_*.c` |
| `osd_clock.c` | 行首锚定 `grep -cE '^[[:space:]]*assert\('` = 0 |
| 发布包文件清单 | 仅 8 个文件（AUTHORS/COPYING/ChangeLog/Makefile/NEWS/README/osd_clock.1/osd_clock.c） |

→ 上游用例数 **0**；无用例被修改（不存在修改上游测试用例的情况）。

## 2. 适配后测试（R51 第二步：真实执行）

`test_package/test_osdclock.sh` 真实执行安装后的 `bin/osd_clock`，5 条用例 / 9 条断言，
全部无需 X server、对真机显示状态零副作用：

| # | 用例 | 期望 | 依据（上游源码行） |
|---|------|------|-------------------|
| 1 | `-h` | rc=0 且输出含 `USAGE:` | `osd_clock.c:96-107`（getopt 后立即 return，早于 `xosd_init()`） |
| 2 | `--help` | rc=0 且输出含 `USAGE:` | 同上（getopt_long 长选项） |
| 3 | `-c red`（无 DISPLAY） | rc=1 且输出含 `Error initializing osd` | `osd_clock.c:112-117` + libxosd 2.2.14 `src/libxosd/xosd.c:715-719`（`XOpenDisplay` 失败 → `xosd_init` 返回 NULL） |
| 4 | `-f fixed -o 5 -t -d 2`（无 DISPLAY） | rc=1 且输出同一串 | 证明选项被正常解析而非提前退出 |
| 5 | `readelf -d bin/osd_clock` | `NEEDED` 含 `libxosd.so.2` | 证明链接的是被测包本体 |

**用例 3 兼具回归探针作用**：`patches/0002` 未修时，aarch64 上 `char` 无符号使
`(c = getopt_long(...)) != -1` 恒真，程序在 `xosd_init()` 之前空转；脚本以
`timeout 60` 兜底判 FAIL（打补丁前实测 rc=124 挂死，打补丁后 rc=1）。

## 3. 实测结果

```
== osdclock 0.5 test_package: <pkg>/bin/osd_clock
  ----  -h -> rc=0
  PASS  -h: exit code (=0)
  PASS  -h prints usage banner
  ----  --help -> rc=0
  PASS  --help: exit code (=0)
  PASS  --help prints usage banner
  ----  -c red (no X display) -> rc=1
  PASS  -c red (no X display): exit code (=1)
  PASS  -c red reports init failure
  ----  -f fixed -o 5 -t -d 2 (no X display) -> rc=1
  PASS  -f fixed -o 5 -t -d 2 (no X display): exit code (=1)
  PASS  option combination reaches init failure
  PASS  DT_NEEDED links libxosd (=libxosd.so.2)
HMBS_TEST_PACKAGE_RESULT={"total":9,"passed":9,"failed":0}
```

- 上游用例通过率：**0/0**（上游无测试套件，见 §1）
- 新增（test_package）用例通过率：**5/5（100%）**；断言通过率：**9/9（100%）**
- `conan create`（G2）：PASS；`conan-verify` G1–G4 + L2/L4/L5：PASS
- W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）：PASS（1/1，L0 全过、L1 test_package executed）

### 已知非阻塞项

- W3 的 L2 "smoke test" 直接执行 `bin/osd_clock --version` / `--help`，**不注入依赖
  `libdir` 到 `LD_LIBRARY_PATH`**；本包为动态链接 libxosd 的 CLI，故该通用探针无法加载
  `libxosd.so.2`（`L2_RESULT=skip`，框架标注 non-blocking）。test_package 在同一次
  W3 运行里真实执行了该二进制并全绿（L1_RESULT=pass），功能覆盖不受影响。
- `finish` step 3 的 G0 clean-verify 按 autotools 约定执行 `configure`，而本包上游
  是手写 Makefile（无 configure）→ 报 `configure 失败 (exit 127)`；框架标注为非阻塞，
  且 step 4 的 `conan-verify`（G2 真 `conan create`）为 PASS，构建正确性以 G2/W3 为准。
- `finish` step 6 的 `packaging/` 缺失为框架 v2.0 遗留误报（R19 禁手工 tar 打包），
  详见 PR 补充说明。
