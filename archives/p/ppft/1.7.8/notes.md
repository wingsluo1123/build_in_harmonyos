# notes — ppft 1.7.8 适配 HarmonyOS PC

## 结论速览

- 纯 Python（noarch，顶层 `ppft/`），**零编译**；产物 = `lib/python3.12/site-packages/ppft/`
- **零运行期依赖**：PyPI `requires_dist` 为空（`dill>=0.4.1` 仅为可选 extra）
  → 不声明任何 Conan `requires`（无需 pip 绕过、无需随包附带）
- 上游测试：sdist 内测试目录**动态探测**（`tests/` → `ppft/tests/` → `test/`）；
  **探测不到即响亮失败**（不冒充通过）；测试期依赖 `dill` + `pytest` 装到 `<build>/test-deps`

## 关键实测点

1. **依赖判定**：`requires_dist` 为空 → "已合入 > 可绕过" 的顺序在此直接落到"无需任何依赖处置"，
   这是最省事的形态；manifest 的 `dependencies` 如实写 `（无）` 并注明 dill 是可选 extra。
2. **测试布局未亲验**（取 sdist 需网络，本轮网络故障）→ 配方写 `_discover_test_dir()`：
   依次探测 `tests/`、`ppft/tests/`、`test/`，命中条件是该目录下有 `test*` 开头的文件；
   **都探测不到就 `ConanInvalidConfiguration` 抛错并打印 sdist 顶层内容**，
   便于本地 CI/CI 一次性给出真实布局（而不是静默跳过）。
3. **测试期依赖**：`dill>=0.4.1`（上游测试大量使用）+ `pytest`（本环境自带），
   pip 到 `<build>/test-deps`（**不进产物**）；先清华镜像、失败退回官方源。
4. **PYTHONPATH 顺序**（prawcore 教训）：`pkg → test-deps → 原环境`；
   `build()`/`test()` 里的 subprocess **不继承** conan 依赖 env，必须显式前置。
5. **OHOS 沙箱**：`/tmp` 只读 → `TMPDIR=/data/storage/el2/base/cache`。
6. **不依赖 curl**：取源用 conan `get()`（sha256 校验），测试期依赖用 `python -m pip`。

## 待办（网络恢复后）

1. 本地 `conan create` 跑通 → 回填 `upstream_test_pass_rate`（真实数字，不替跑）；
   若测试布局与候选不符 → 按 CI 输出修正 `TEST_DIR_CANDIDATES`。
2. 消费者校验实测回填（期望 `checks=6 fails=0 skips=0`）。
3. 提交 push → 建 PR（#8597 模板）+ issue 互链。

## 测试期 shim（重要披露：只改并行度，不改用例与断言）

CI 构建 **#89931** 失败根因：上游并行用例 `ppft/tests/sum_primes_functor.py` 调用**无参**
`pp.Server(ppservers=())`，而 `Server._Server__detect_ncpus()` 在 Linux 下取
`os.sysconf("SC_NPROCESSORS_ONLN")`（**系统总核数**；实测与 CPU 亲和性无关——本机限到 2 核后
仍是 20），于是**一次 spawn 出与核数相同的 worker 进程**，CI 沙箱的进程配额撑不住：

```
File ".../ppft/_pp.py", line 146, in start
    proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, ...)
BlockingIOError: [Errno 11] Resource temporarily unavailable: '/data/service/hnp/bin/python3'
```

处置（仅测试期，**不碰上游源码与断言**）：

1. **并行度 shim**：`<build>/test-shim/sitecustomize.py` 把 `_Server__detect_ncpus()` 的返回值
   压到 **2**（子进程经 PYTHONPATH 继承）。用例数、断言、通过判定完全不变，只是并行度降低。
2. **shim 自检（必须）**：直接问 ppft 探测值，`> 2` 一律 `ConanInvalidConfiguration`。
   实测踩过：首版 shim 把类名写成 `_Server`（真实类名是 **`Server`**）→ `getattr` 得 `None`
   **静默跳过**、日志仍是 `Starting pp with 20 workers`；加硬守卫后不可能再静默失效。
3. **有界重试**：仅当输出命中沙箱瞬时资源错误特征（`BlockingIOError` /
   `Resource temporarily unavailable` / `Errno 11` / `Cannot allocate memory` / `Too many open files`）
   时重试 **1 次**；断言失败一律不重试。

实测（本地 conan create）：
```
[upstream tests] shim 自检通过：ppft 探测到 2 个 worker（上限 2）
[upstream tests] Starting pp with 2 workers          ← shim 生效前是 20
[upstream tests] 上游套件 7/7 个脚本全部通过（rc=0，上游 runner ppft/tests/__main__.py）
```

## 上游测试统计

| 项 | 值 |
|---|---|
| 测试位置 | 待实测（动态探测：`tests/` / `ppft/tests/` / `test/`） |
| 运行命令 | `python3 -m pytest <探测到的目录> -q` |
| 实测结果 | **待回填**（本轮无网络，不臆测数字） |
| 修改上游用例 | **否**（原样使用） |

## 路径判定

未命中路径 C 四项条件（纯 Python、**零外部依赖**、无私有系统接口/工具链/汇编/闭源二进制）
→ 属**路径 A 基础适配**；本库**不再新增知识草稿**（其候选经验与 `E429-draft-6FBA`
的"测试路径核对"高度重合，按查重口径避免重复草稿）。
