# DRAFT: CI Worker 瞬时进程耗尽（clang posix_spawn EAGAIN）的配方内有界重试

## 错误特征

```
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
pqclean/0.0-git.0586a82: ERROR: Error in build() method, line 127
	ConanException: Error 1 while executing
```

正则签名（机器匹配）：

```
clang-1[0-9]?: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable|posix_spawn failed: Resource temporarily unavailable
```

## 现场特征（识别要点）

- **此前一切成功**：库源对象逐个编译完毕、静态库归档完毕，仅在后续某条
  spawn 子进程命令（如 functest 链接）单点失败；
- **无任何编译诊断**（fatal error/undefined reference 均无）——不是代码问题；
- **单 worker 出现**（本例 CI-010；换 worker CI-001 即绿）；
- 本机同 profile `conan create` 全绿——排除源码/配方缺陷。

## 根因

CI Worker 节点瞬时进程/资源耗尽：clang 驱动进程派生子进程（cc1/ld）时
`posix_spawn` 返回 EAGAIN。这是 worker 侧瞬时状态，与被构建软件无关。
旧处置（纯 /rebuild 重试）能绿但烧轮次且不可控；配方内吸收更稳。

## 解法（代码级）

`conanfile.py` 中把编译/归档/链接类 `self.run` 路由到有界重试 helper：

```python
_TRANSIENT_SPAWN_RE = re.compile(
    r"posix_spawn failed|Resource temporarily unavailable", re.IGNORECASE)

def _run_resilient(self, command):
    for attempt in range(1, self._SPAWN_ATTEMPTS + 1):   # 4
        buf = io.StringIO()
        try:
            self.run(command, env="conanbuild", stdout=buf, stderr=buf)
            return
        except ConanException:
            output = buf.getvalue()
            if output:
                self.output.writeln(output)     # 回放原始诊断
            if attempt >= self._SPAWN_ATTEMPTS or not self._TRANSIENT_SPAWN.search(output):
                raise                            # 真错误首试即抛
            time.sleep(self._SPAWN_RETRY_BASE_DELAY * (2 ** (attempt - 1)))  # 5/10/20s
```

### 匹配边界（红线）

- **只匹配 errno 串**（`posix_spawn failed` / `Resource temporarily
  unavailable`）。`unable to execute command` 前缀**不能**单独匹配——clang
  对永久性错误（如找不到可执行文件）也用该前缀，单独匹配会把真错误吞进
  重试循环、拖慢 CI 且最终语义混乱；
- 其他任何非零退出**首试即抛**且回放原始输出——真实编译错误的红绿语义
  完全不变；
- 退避 5s→10s→20s、4 次上限（最坏 35s），对 CI 时限无感。

## 降级方案

重试耗尽（>4 次持续 EAGAIN）= worker 病重：纯 `/rebuild` 换 worker；
多 worker 同款失败 = 确定性问题（代码/冲突），按 R43/R44 停损上报，
禁止继续盲目重试。

## 验证

| 项 | 值 |
|---|---|
| 原始失败 | CI build 105508（#91805，CI-010），build() L127 |
| 修复 | PR #14587 commit bcab6ccab9 |
| 本机 | ohos-aarch64 profile conan create 全绿两轮（10/10 断言） |
| CI | #91882 通过（CI-001，2026-10-14 22:40） |

## 与相近条目的区别（查重）

- E055/E405/DRAFT-4033：musl **Python** 的 `posix_spawn` 语义差异
  （_USE_POSIX_SPAWN/裸命令不走 PATH）——**语义**问题，非资源耗尽；
- E253：ocaml `posix_spawn` 相对路径 ENOENT——路径解析，非 EAGAIN；
- DRAFT-libuev：运行时 **signalfd** EAGAIN 虚假可读——运行时语义，
  非编译期 spawn；
- 本条：**CI Worker 瞬时资源耗尽**（编译期 clang spawn 子进程 EAGAIN）+
  配方内有界重试吸收模式，四范围查重无同根因条目。
