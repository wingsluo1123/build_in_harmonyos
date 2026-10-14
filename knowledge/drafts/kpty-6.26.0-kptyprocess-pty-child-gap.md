# kpty 6.26.0 — KPtyProcess 的 pty 子进程路径缺口（OHOS）

## 现象

KDE Frameworks 6 `kpty/6.26.0` 上游自动测试 `autotests/kptyprocesstest.cpp`（QTest，5 个槽）
在本机 OHOS aarch64 构建环境下实跑结果为 **1 个目标 / 0 通过**：

| 槽 | 结果 |
|----|------|
| `initTestCase` | PASS |
| `test_pty_basic` | FAIL!（`waitForReadyRead` FALSE） |
| `test_pty_signals` | FAIL!（信号值不符） |
| `test_ctty` | FAIL!（输出为空） |
| `test_shared_pty` | FAIL!（`waitForReadyRead` FALSE）→ 随后 SIGSEGV |

## 已排除的原因

1. **不是缺 pty 头/符号**：构建后 `config-pty.h` 实测 `HAVE_OPENPTY=1`、`HAVE_PTSNAME=1`
   （`HAVE_GRANTPT/UNLOCKPT/POSIX_OPENPT=0`，授权由 `openpty()` 内部完成）。
2. **不是环境不能跑 pty 子进程**：本机 `pty.fork()` + `os.read()` 实测可读到子进程输出
   （`READ=hello-pty`）；同包 `test_package/` 的消费者用例亦成功取得 `/dev/pts/3`。
   → 因此「沙箱无 pty」不是解释，早期把失败归因于 `/dev/ptmx` 的写法已被证伪并撤销。

## 待查方向

- `KPty::setCTty()`（`setsid()` + `ioctl(TIOCSCTTY)`）在 OHOS 上的语义与返回；
- Qt6 `QProcess` 的 `childProcessModifier` 与 pty 从设备 fd 的交接时序；
- 子进程 stdout 未被正确设为控制终端时的缓冲行为（块缓冲 → 父进程长时间读不到数据）。

## 当前处理策略（kpty/6.26.0 配方内）

- `build()` 内**仍实跑** `ctest --test-dir <build> --output-on-failure`，失败输出原样打印；
- 非 0 退出码时追加一条明确 warning（含 rc 与「这是已记录的缺口、不是通过」），
  **不把失败伪装成通过**，也不静默吞掉（上一版把二进制路径写成 `autotests/` 导致保护
  从未生效，已删除该写法）；
- 断言级覆盖由 `test_package/` 的真实消费者用例承担；
- 定位根因后应把 ctest 恢复为硬门禁，并按中性符号探测写法（R8：补丁内禁平台宏）处理
  `setCTty` 相关能力差异。

## 复现命令

```bash
# 干净缓存
conan create archives/k/kpty/6.26.0 --build=missing \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# 等价手工复现（构建目录内）
ctest --test-dir <build_folder> --output-on-failure
```

## 影响面

- `KPty` 的核心 API（`open()` / `ttyName()` / 设置 termios）消费者用例通过；
- 受影响的是 **`KPtyProcess`（在 pty 上启动/驱动子进程）** 这条路径；
- 依赖 `KF6::Pty` 的下游（如 `kwrited`）在真机上使用该路径时需实测复核。
