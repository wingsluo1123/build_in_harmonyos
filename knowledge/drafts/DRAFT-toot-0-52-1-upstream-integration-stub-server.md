# DRAFT-TOOT-INTEGRATION-STUB: 上游集成测试被"外部服务"门控时，用配方自带 stdlib 桩服务把执行率提满

- 条目主题：纯 Python（及其它语言）上游包自带 `tests/integration/` 一类"需要外部服务才能跑"的测试时，如何在 HarmonyOS PC 适配中**真实执行**它们，而不是以 skip 交差；以及"上游测试用例通过率"分母口径的正确算法。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 来源任务：toot 0.52.1 HarmonyOS PC aarch64 适配（PR !15046 审核意见 193803344，规则 4 条件 2 FAIL）
- 关联先例（本仓库已合并）：`archives/r/restclient-cpp/0.5.3/files/loopback_httpbin.py`、`archives/l/libetebase/0.5.8/etebase_stub_server.py`

## 适用场景

申报的上游用例数为 N，`build()` 里实际执行的只有少数，其余被 `pytest.skip` /
`SKIP (needs a running X)` / `add_test(... )` 环境检查屏蔽。典型触发形态：

```python
@pytest.fixture(scope="session")
def base_url():
    if not os.environ.get("TOOT_TEST_BASE_URL"):
        pytest.skip("Skipping integration tests, TOOT_TEST_BASE_URL not set")
```

审核口径（`docs/TEST_QUALITY_SPEC.md` 规则 4 条件 2）认定这属于"上游绝大部分
测试未运行"，FAIL。以 toot 为例：申报 152，实跑 36（24%）。

**关键认知**：这类 skip 几乎从不是"真的跑不了"，而是"没人给它搭环境"。判
断能不能跑之前，先按下面的顺序穷举手段。

## 分母口径（先算对，再谈整改）

| 指标 | 算法 |
|---|---|
| 收集 | `pytest tests --collect-only -q` 末行数字（**不要用申报文件里的数字反推**） |
| 实际执行 | 收集数 − skip 数 |
| **执行覆盖率** | 实际执行 / 收集 |
| **通过率** | passed / **收集数**（不是 passed / 已执行数） |

把"36/36（100%）"当成绩是自欺：分母必须是全量收集数。toot 整改后为
152 收集 / 152 执行 / **150 passed（98.68%）** / 2 skipped。

## 手段优先级（逐档穷举，每档都要留下"为什么不行"的实测证据）

1. **上游真实栈**：Docker/podman/compose。本仓库场景通常不可得 —— 设备与 CI
   worker 都没有容器运行时，且可重复构建不接受外网/凭据依赖。
2. **原生依赖就地安装**：如 postgres/redis。看制品仓有无配方；没有且无法适配
   （Rails 需未适配的原生 gem）即排除。
3. **⭐ 纯 stdlib 有状态桩服务（loopback）**：本条目主题。上游测试打的是
   HTTP/ socket，桩在 `127.0.0.1:<port>` 真起服务，用例经真实 client 库收发。
4. **进程内 mock（monkeypatch client）**：仅当被测代码的 HTTP 层被完全屏蔽，
   等于没测 transport/序列化/分页/重试，执行率口径上应视为**未真实执行**，
   不要拿它冒充第 3 档。
5. 实在只剩第 3 档也覆盖不到的，逐条给技术原因 + 证据。

## 第 3 档落地要点（配方侧）

```python
STUB_HOST, STUB_PORT = "127.0.0.1", 3000   # 端口常被上游断言写死，先 grep 测试源码

def export_sources(self):
    copy(self, "test_support/**", src=self.recipe_folder,
         dst=self.export_sources_folder, keep_path=True)  # 只进构建上下文

def _stub_script(self):                    # 导出位置随构建方式变化，逐个候选探测
    rel = os.path.join("test_support", "mastodon_api_stub.py")
    for attr in ("recipe_folder", "export_sources_folder",
                 "base_export_sources_folder", "base_source_folder",
                 "source_folder"):
        base = getattr(self, attr, None)
        if base and os.path.isfile(os.path.join(base, rel)):
            return os.path.join(base, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)

def _start_stub_server(self):
    proc = subprocess.Popen([sys.executable, script, "--host", STUB_HOST,
                             "--port", str(STUB_PORT), "--verbose"],
                            stdout=log_file, stderr=subprocess.STDOUT, env=env)
    # 就绪判定用 HTTP 探测而非 sleep；每轮先看 proc.poll() 以便早退时带日志报错
    ...

def _run_upstream_tests(self):
    stub, log_file, log_path = self._start_stub_server()
    env["TOOT_TEST_BASE_URL"] = f"http://localhost:{STUB_PORT}"   # 注意 host 字面量
    try:
        proc = subprocess.run(cmd, ...)
    finally:
        self._stop_stub_server(stub, log_file)                     # 必须 finally 收尾
```

三条硬要求：

- **不进包**：`package()` 从 `stage` 拷贝，桩只在 `export_sources()` 里。改完
  要核对打包文件数没变（toot 仍 129 个 `.py`）。
- **留痕**：桩以 `--verbose` 落访问日志，构建日志打印请求数。`725 API
  request(s)` + `52 个去重路径` 是"真打了网络"的最有力证据；服务端 0 个
  Traceback、负例路径命中 401/404/422 可反证错误分支也真跑到了。
- **失败要响**：桩起不来（端口被占）必须抛 `ConanException` 并附桩日志尾部，
  绝不允许退化成"跳过继续"。

## 桩服务的实现坑（HTTP API 类通用）

按踩中概率排序，全部来自 toot×Mastodon 实测：

1. **地址/端口字面量**：测试里 `assert app.base_url == "http://localhost:3000"`
   会把端口和 host 一起钉死。桩把"实例 URI"字段回写成请求的 `Host` 头，任何
   host 都自洽；端口只能照抄。注意 `localhost` 与 `127.0.0.1` 在断言字符串里
   不等价。
2. **分页 Link 头**：Mastodon 形如 `<path?max_id=X>; rel="next", <...>;
   rel="prev"`。客户端常按**行首 `<` + `rel="next"`** 前缀正则解析，故 `next`
   必须排在 `prev` 之前，且**只在真有后续条目时发出**——多发一条就死循环翻页。
3. **时间戳格式**：实体层解析往往宽容，但**测试自己**会 `strptime(..., "%Y-%m-
   %dT%H:%M:%S.%fZ")`，必须带 6 位小数与字面 `Z`。
4. **布尔查询参数**：`?exclude_replies=True` 传的是字符串，要按
   `"True"/"true"/"1"` 判真，否则过滤类断言全红。
5. **错误文案逐字**：客户端把 API error body 直接渲染成 `Error: <原文>`，
   `Record not found` / `Record invalid` / `You have already voted on this
   poll` 差一个字符即失败。Mastodon 还有一处反直觉行为（多选取单选时仍返回
   "already voted"）也要照抄。
6. **二进制元数据**：媒体上传的宽高要真解析（PNG 走 IHDR
   `struct.unpack(">II", payload[16:24])`），测试资源若是 webm 则把 ffmpeg
   实测值硬编码并注明来源。
7. **默认值不要"好心"填**：如 `display_name` 必须默认空串，否则
   `assert stdout == "Accounts:\n* @user"` 失败。
8. **空结果的确切输出**：渲染函数的分隔线可能在循环体内，0 条时只剩一条——
   测试断言的是 `"─" * 80`，桩返回空数组才是正确行为。
9. **状态写入语义**：预约/调度类接口在成功时**不得**立即发布；删除后再 GET
   必须 404。
10. **一次登录发新凭据**：复用 token 会让 re-login 类用例失去判别力。

## 依赖版本也会伪装成"跑不了"

toot 的 7 条集成用例在 click 8.1.x 下以
`ValueError: stderr not separately captured` 失败 —— 因为
`click.testing.CliRunner()` 旧默认 `mix_stderr=True`，8.2 起移除该参数并独立
捕获 stderr。桩没问题、网络没问题，纯粹是测试框架版本。上游约束 `click~=8.1`
允许 8.4.2，锁 8.4.2 后 13/13 通过。

**推论**：执行率整改失败时，先核对测试框架（click/pytest/werkzeug 一类）版本，
再怀疑自己的桩。

## 上游主动 skip 的部分怎么办

上游在测试函数体第一行写 `pytest.skip("TODO: fix mocking")` 的用例（toot 有 2
个），在**上游自己的 CI 上同样是 skipped**。适配不改上游测试源码，因此保留
skip，但在报告里逐条给：文件:行号、skip 语句原文、`pytest -rs` 输出。这类
"上游声明的不执行"与"环境不具备"要分开表述，不要混为一谈。

## 验证命令

```bash
# 分母与执行率
TOOT_TEST_BASE_URL=http://localhost:3000 python3 -m pytest tests -q -rs
# 逐用例留痕
TOOT_TEST_BASE_URL=http://localhost:3000 python3 -m pytest tests -v | tee upstream-suite-verbose.log
# 网络真实性
grep -c '^stub: ' mastodon_api_stub.log          # 请求数
grep -c Traceback mastodon_api_stub.log         # 必须为 0
grep -vE '" 20[0-9] -' mastodon_api_stub.log | grep '^stub: '   # 负例命中
```
