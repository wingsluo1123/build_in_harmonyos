# Python 复刻构建驱动在受限 OHOS worker 上撞 fork 压力（BlockingIOError EAGAIN）

Status: DRAFT
Source: xd 5.00.03（conanfile.py 里用 Python 复刻 icmake/icmbuild 的构建驱动）
触发事件：PR #15428 第三轮 CI（同一份代码前一轮 68 TU 编译通过，本轮在 build() 抛 EAGAIN）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| DRAFT-yasw-0.6-qmake-probe-fork-pressure-empty-output | 宿主 fork 压力导致 qmake 编译器探测 **Output 段为空**，处方是"有限重试，改 PATH 无效" | 该条触发点在构建系统自身的探测子进程里、症状是"空输出"；本条触发点在**配方自己的 Python 并发驱动**（ThreadPool + shell=True），症状是显式 `BlockingIOError: [Errno 11]`，处方是"并发上限 + 免 shell + 瞬时 errno 有限重试" |
| DRAFT-libuev-2.4.1-ohos-fork-signalfd-eagain-spurious | fork/signalfd 场景下 EAGAIN 的伪失败语义 | 那是**运行期**程序逻辑面对 EAGAIN 的处置；本条是**构建期**配方并发模型的收敛策略 |
| E003 / E085（AppSpawn 相关） | OHOS 进程管控/弹窗语义 | 未涉及构建并发上限与 argv/shell 进程数的关系 |

检索关键词：`EAGAIN`、`Resource temporarily unavailable`、`BlockingIOError`、`fork`、`ThreadPool`、`shell=True`。
结论：库内已有"fork 压力"家族条目，但都发生在**上游构建系统内部**；"配方自身 Python 并发驱动"的收敛与重试口径未被覆盖 → 判定为本条增量。

## Scope（何时使用）

- conanfile.py 用 Python（ThreadPool/多进程/subprocess）驱动大量编译/链接命令；
- 目标环境是 OHOS 设备/CI worker（进程创建受 AppSpawn 管控）；
- 症状是**间歇性** `BlockingIOError: [Errno 11] Resource temporarily unavailable`，同一份代码有时过、有时不过。

不适用：确定性编译错误（应修源码/补丁）；一次性的网络/registry 故障（走依赖类处置）。

## Symptom（真实日志，PR #15428 第三轮 CI）

```
oxd/5.00.03: xd 源文件: 68 个翻译单元
oxd/5.00.03: ERROR:
oPackage '0042903af…' build failed
oERROR: xd/5.00.03: Error in build() method, line 243
o       for cmd, rc in zip(compile_cmds, pool.imap(run_one, compile_cmds)):
o       BlockingIOError: [Errno 11] Resource temporarily unavailable
```

注意异常抛出的行（`pool.imap` 消费循环）只是**表层**：真正的失败是子进程 spawn（fork/pipe）拿到 EAGAIN。

## Root Cause

`ThreadPool(N≈CPU 数)` + `subprocess.run(..., shell=True)` ⇒ 每条编译命令 = `/bin/sh` + 编译器两个进程 ⇒
瞬时进程数 ~2N；worker 侧进程/pipe 资源吃紧时 fork/pipe 返回 EAGAIN，`subprocess.run` 抛
`BlockingIOError`。因为压力是瞬时的，表现就是"同一代码时好时坏"。

## Recommended Fix

1. **并发收敛**：`jobs = max(1, min(int(build_jobs(self)), 4))`（`build_jobs` 只当上限参考）。
2. **免 shell**：命令改 argv 列表（`subprocess.run([cxx, ...])`）——每条命令 1 个进程，顺便免去手工引用路径。
3. **瞬时错误有限重试**（只针对 errno）：
   ```python
   _TRANSIENT_SPAWN_ERRNOS = frozenset({errno.EAGAIN, errno.ENOMEM, errno.EMFILE, errno.ENFILE})
   ...
   except OSError as err:            # BlockingIOError 是 OSError 子类
       if err.errno not in _TRANSIENT_SPAWN_ERRNOS:
           raise                     # 例如 ENOENT：立即失败，不掩盖
       log.write(f"[retry {attempt}/{attempts}] spawn failed: {err}\n")
       time.sleep(1.0 * attempt)
   ```
   重试 3 次；用尽后抛 `ConanException`（附命令与最后一次 errno）。编译/链接**自身**的非零退出码不做重试。
4. 把 `[retry i/3]`、并发数与编译日志写进 `xd_compile_log.txt`，CI 可追溯。

## Fallback

串行编译（`jobs=1`）：进程压力最低、必定能过，代价是编译时间线性上升；适合 TU 少或首轮打通 CI。

## Forbidden Approaches

- ❌ 加大并发/`-j` 去"解决" EAGAIN（方向相反，压力更大、失败点漂移）。
- ❌ 对 spawn 失败或编译错误做无差别 `except: pass`（链接期报缺对象/符号，掩盖真因）。
- ❌ 并发路径继续用 `shell=True`（进程数近似翻倍；路径错误还会伪装成 shell 语法错误）。

## Verification

```bash
# 同型构建（CI 语义）
conan create archives/x/xd/5.00.03 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：编译并发 4 → 68/68 TU → 链接 → 打包；若命中瞬时压力，日志出现
#   [retry 1/3] spawn failed: [Errno 11] Resource temporarily unavailable
#   然后继续成功
```

本地单元验证（配方方法级）：EAGAIN 一次→重试后成功；ENOENT→立即抛出（不重试）；持续 EAGAIN→3 次后抛 `ConanException`。

## Prevention

- 预检/评审 Python 构建驱动时检查两点：并发是否被 CPU 数直接驱动、命令是否经 shell 下发。
- 关键词：`ThreadPool`、`pool.imap`、`shell=True`、`BlockingIOError`。

## 适用范围 / 不适用范围

| 维度 | 内容 |
|---|---|
| 适用 | 配方自研并发驱动；受限 worker（OHOS）；间歇性 EAGAIN/ENOMEM/EMFILE/ENFILE |
| 不适用 | 确定性编译错误；网络/registry 故障；上游构建系统自身的 fork 压力（见 yasw 条，处置重点不同） |
| 前置条件 | 能区分"spawn 失败"与"编译失败"（errno vs 退出码） |
| 应转用其他知识 | 上游探测子进程空输出 → yasw 条；运行期 EAGAIN 语义 → libuev 条；进程管控/弹窗 → E003/E085 |

## References

- 触发：PR #15428 第三轮 CI 日志（`build()` 抛 BlockingIOError EAGAIN）
- 实现：`archives/x/xd/5.00.03/conanfile.py`（`_build_jobs()`、`_run_with_retry()`、argv 化编译/链接命令）
- 同型写法（潜在风险）：`archives/b/bobcat/6.14.00/conanfile.py`（`ThreadPool(build_jobs)` + `shell=True`）
- 同族条目：DRAFT-yasw-0.6-qmake-probe-fork-pressure-empty-output、DRAFT-libuev-2.4.1-ohos-fork-signalfd-eagain-spurious
