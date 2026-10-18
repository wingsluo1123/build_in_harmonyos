# E610 — CI worker 沙箱 ≠ 设备原生：测试里写死的环境假设必然翻车（`sys.platform` / chmod 保真度 / AF_UNIX `EPERM`）

> 草稿态（`knowledge/drafts/E610-draft-A14E.kv`），未进正式索引；正式 E 编号待 `graph promote` 分配。
> 来源适配：`archives/s/synadm/0.49.2`，PR #15991 **首轮远端 CI 红**（`Ran 15 tests … FAILED (failures=2, errors=1)`）。

> 既有未晋升草稿 `DRAFT-10004-qtwayland-qt-tests-deep-path-socket-tmpdir-qpa` 记录了深路径下
> socket/tmpdir 引发的测试环境问题。本条的增量是**判定口径**：同一份平台特性用例要在
> "设备原生"与"CI worker 沙箱"两套环境都成立，因此**能力必须运行时探测、断言只锁安全属性**。
> 晋升时请与上述草稿合并。

## 错误特征

三条失败同时出现在同一套用例里，而**被测软件本身毫无问题**：

```
FAIL: test_python_reports_posix_so_upstream_branches_are_taken
      self.assertTrue(sys.platform.startswith("linux"))     → AssertionError: False is not true

FAIL: test_write_config_takes_posix_branch_and_restricts_mode
      self.assertEqual(mode, 0o600, …)                      → AssertionError: 416 != 384   # 0o640

ERROR: setUpClass (Test02UnixSocketTransport)
      socket.socket.bind(self.socket, self.server_address)
      → PermissionError: [Errno 1] Operation not permitted
```

注意第三种：`setUpClass` 里 `bind()` 抛 `EPERM`，导致**整个测试类 error**——连该类里
根本不需要 socket 的用例（vendored 库来源校验）也一起没了覆盖。

## 触发条件

用例的断言/装配直接引用了只在**一种环境**实测过的结论：

| 维度 | 设备原生（本机） | CI worker 沙箱 | 差异来源 |
|------|------------------|----------------|----------|
| `sys.platform` | `linux` | 非 linux 前缀 | 运行时/沙箱差异 |
| `chmod 0600` 落地 | `0o600` | `0o640` | 挂载 / ACL 追加 group 位 |
| `AF_UNIX bind()` | 允许 | `EPERM` | 沙箱安全策略 |

## 根因

把**环境能力**误当成**产品契约**：

1. 断言 `sys.platform` 前缀 —— 真正的前提是 `os.name == "posix"`（实测：该库全量源码 **0 处**
   读 `sys.platform`），锁错了对象即为假失败。
2. 断言具体八进制权限 —— 落地位由挂载决定，软件只能保证"other 无访问位 + 无 group 写/执行位 + owner 可读写"。
3. 未探测就 `bind()` —— 能力缺失时用**异常传播**（error）而非**跳过**（skip）表达，
   连带吞掉同类的非 socket 用例。

## 推荐做法

```python
# ① 锁软件真正依赖的前提，取值只进失败信息
self.assertEqual(os.name, "posix", f"os.name={os.name!r} sys.platform={sys.platform!r}")

# ② 权限锁安全属性，挂载差异只记录
mode = os.stat(config_path).st_mode & 0o777
self.assertEqual(mode & 0o037, 0)          # other 无访问位 + group 无写/执行位
self.assertEqual(mode & 0o600, 0o600)      # owner 可读写

# ③ 能力探针 → 不支持则 skip（理由=实测 errno），套件保持 rc=0
def _probe_af_unix(candidates):
    reasons = []
    for cand in candidates:
        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(os.path.join(cand, ".afunix-probe.sock"))
            return cand, True, ""
        except OSError as exc:
            reasons.append(f"{cand}: [Errno {exc.errno}] {exc.strerror}")
        finally:
            if sock: sock.close()
    return candidates[0], False, "; ".join(reasons)

class Test02UnixSocketTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = _start_unix_stub() if AF_UNIX_BINDABLE else None

    def require_socket(self):
        if self.server is None:
            raise unittest.SkipTest(f"no AF_UNIX bind in this sandbox: {AF_UNIX_BIND_REASON}")
```

## 验证

- 设备原生：`Ran 42 tests … OK` + `Ran 21 tests … OK`（63/63，无 skip）。
- CI worker：套件 A `Ran 42 … OK`；套件 B `16 PASS + 5 SKIP`，rc=0。
- 报告里以**环境矩阵**给出两个数字，不用一个数字掩盖差异（`reports/test-report.md` §3.4）。

## 反面模式（禁止）

- 断言平台字符串前缀（`sys.platform.startswith(…)`）。
- 断言具体 chmod 八进制数（`… & 0o777, 0o600`）。
- `setUpClass` 内未探测就 `bind()`。
- 用 `except OSError: pass` 把"起不了服务端"伪装成"传输验证通过"——绿灯但零覆盖，比红更危险。
