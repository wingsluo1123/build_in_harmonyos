# 上游测试套件在 OHOS 上引导实战：执行位异常 + 平台运行时缺陷（GHC testsuite 实证）

> 来源：ghc-ohos/9.12.2 适配的 rule4 彻底实测（2026-10-15/16，PR #13664）
> 适用：任何"上游测试套件需要编译并**执行**产物"的包（GHC/LLVM/编译器类、
> 带 should_run 类用例的测试框架），以及任何依赖 shell 输出的上游脚本。

## 一、先把"测不了"这句话变成可核验的断言

rule4 的判定口径（仓库多处实证）：

1. 上游测试必须**真实执行**（`archives/a/argparse/3.2/notes.md`：rule 4 实测回填）；
2. **申报的 N 不得少报**（平台会做上游双重核验；`accountsservice` 实测 N=19 > 声明 N=0
   被打回；`asterisk-ldap` 只报 `tests/` 子集 633、全树 707 被驳回）；
3. 台账自洽：`sum(gaps) == official_total - passed`（`alberta` conanfile 注释）。

因此"不可执行"必须给出：**精确 N + 阻断机制 + 阻断点的实测复现**，三样都缺就会被
当成"没试"。

## 二、用例级计数 ≠ 文件级计数（本轮最大教训）

GHC 的 `.T` 文件是驱动脚本，一个文件里可定义多个 `test('name', ...)` 用例。

- 按文件数报：596 个 `.T`（testsuite 包）+ 15 个 `all.T`（源码包）= 611；
- 按用例定义报（流式解析全部 `.T` 的 `test(` 定义）：
  **10,070（去重 10,064）+ 299 = 10,369**。

差 17 倍。**申报用文件数 = 少报**，直接触发 rule4 打回。

计数正则（够用，注意 `.T` 用单引号）：

```python
PAT = re.compile(r"\btest\s*\(\s*'([^']+)'")
# 单次流式遍历 tarfile（.T 成员较多，避免对 xz 反复 seek）
with tarfile.open(pkg, "r:xz") as tf:
    for m in tf:
        if m.name.endswith(".T"):
            names.update(PAT.findall(tf.extractfile(m).read().decode("utf-8", "replace")))
```

## 三、缺陷 1：hmdfs/el2 上"新链接的二进制没有执行位"

**现象**（GHC testsuite 实测）：

```
[2 of 2] Linking arr001
Wrong exit code for arr001(normal)(expected 0 , actual 126 )
/bin/sh: ./arr001: can't execute: Permission denied
```

`exit 126` = 文件存在但没有执行权限。实测 `ls -l`：产物模式 **0660**，
即使 `umask 0022` 也一样；而 `ghc-config` 之类自举工具同样 0660，导致
`ghc-config > mk/ghcconfig…` 直接失败、驱动报 `NameError: name
'ghc_compiler_always_flags' is not defined`（被误读成"配置缺失"）。

**判据与修法**：

```bash
ls -l <产物>            # 0660/0640 且无 x 位 → 就是它
chmod 755 <产物> && ./<产物>   # 实测：arr001 立即输出正确结果
```

- 修法首选 `chmod 755`；本平台**同会话 chmod 可能空操作**，兜底做法是
  *复制成新文件再 chmod*（新 inode）；
- 对配方作者：**在签名/链接 shim 里保持执行位**（签名写回同一 inode，
  或 sign 后补 chmod），否则一切"编译产物要运行"的链路（testsuite、
  test_package 的 run-type 断言）都会以 exec 126/ EACCES 收场；
- 注意这**不是**挂载 noexec：同目录里已带 x 位的文件可以正常执行，
  只有"新创建"的文件缺位。

## 四、缺陷 2：本机 python3 的 `os.popen()` 必崩

**最小复现**（本机 `/storage/Users/currentUser/usr/local/bin/python3` 3.12.9）：

```python
>>> import os
>>> os.popen('echo hi', 'r').read()
TypeError: can't concat str to bytes
```

任何命令都一样（`echo hi` / `true` / 管道），**与命令内容无关**。

**影响**：上游脚本里 `os.popen(...).read()` 的每一处都会炸。GHC testsuite
驱动 `driver/runtests.py` 的 locale 探测（`os.popen('locale | grep LC_CTYPE…')`）
因此在**进入测试选择之前**就崩，看起来像"testsuite 完全不兼容本平台"。

**处置**：

- 自己写代码：一律用 `subprocess.run(..., capture_output=True, text=True)`；
- 引用上游脚本走查：定位所有 `os.popen`，给 locale/探测类调用加 `try/except`
  **守卫**（只包探测，不改判定逻辑），并在证据说明里注明"补丁仅用于本机取证"；
- 跨平台判断：这可能只是本机 python 构建问题（hnp python 未及验证），
  先复现再定性。

## 五、缺陷 3：本机 curl 的 CA 库损坏 → 所有 HTTPS 探测都是假失败

```
curl: (60) SSL certificate OpenSSL verify result: unable to get local issuer certificate
```

`curl -I https://any-host` 一律 `000`，**连 gitcode/atomgit 也如此**，很容易
被误判成"外网被墙"。实测：`python3 -c "import urllib.request,ssl;
urllib.request.urlopen(u, context=ssl._create_unverified_context())"` 可以正常
访问 `downloads.haskell.org`（GHC 源码/测试包）与 `codeload.github.com`。

**处置**：本机做 HTTP 探测/下载一律走 python urllib（必要时 unverified 上下文）；
用 curl 的失败结论去推断"网络不可达"前，先用 python 复核一次。

## 五′、缺陷 4：内存压测类测试触发 cgroup 整组清杀（无声，最迷惑）

**现象**（rts 类两次实测复现）：后台作业在该类测试启动瞬间**无声消失**——
无异常输出、无 OOM dmesg、`/proc/meminfo` 显示全局内存充足（32GB 剩 14GB）；
同一用户会话里的**终端进程也一起被关**。

**真因**：进程不在全局内存池里，而在 `4:memory:/100/com.huawei.hmos.hishell_*`
cgroup 中（OHOS 的 hishell 终端会话）。cgroup 限额远小于物理总量，内存压测类
用例（rts 的 stack overflow / 大块分配类）一批启动即打爆限额，内核按 cgroup
**整组清杀**——测试、跑批脚本、终端同组全灭。因是限额触发而非全局 OOM，
dmesg 无从取证。

**判据与处置**：

```
cat /proc/self/cgroup        # 看到 4:memory:/…hishell_* 即命中
```

- 把这类测试**整类排除**（记环境性不可执行），或移出终端 cgroup 单独跑；
- 排查口诀：作业"无声消失 + 全局内存充足 + 同会话终端一起关"，先查
  `/proc/self/cgroup`，别在全局内存里找答案。

## 六、上游 testsuite 在 bindist 上的引导配方（以 GHC 为例，已被验证可跑）

前提：包的交付物是官方 **bindist**，上游测试套件另有官方独立产物
（`ghc-9.12.2-testsuite.tar.xz`，含 `testsuite/` 与 `driver/`）。

1. **落点**：把 testsuite 树解到与包同级的可写树（与 ghc 同一文件系统语义），
   `PATH`/`LD_LIBRARY_PATH` **强制前缀**指向包的 `bin`/`lib`
   （注意 `setdefault("PATH", …)` 对已存在的 PATH 无效——必须直接赋值，
   否则子进程里 ghc 找不到 shim，报 `could not execute: gcc`）；
2. **引导**：`make boot TEST_HC=<abs>/bin/ghc PYTHON=<python3>`。
   - `timeout` 是 **python 包装器**（非 Windows 分支），无需自举编译；
   - `ghc-config` 会**编译链接成功但 exec 被拒**（缺陷 1）→ chmod 755 后
     重跑即可产出真值 `mk/ghcconfig…`（763 字节：`TargetARCH_CPP=aarch64`、
     `RTSWay=rts_thr_dyn` 等）；
3. **驱动入口必须走 make**：`make -C tests test TEST=<name> THREADS=n
   SKIP_PERF_TESTS=YES`。
   直接调 `driver/runtests.py` 会 `NameError: name 'ghc_compiler_always_flags'
   is not defined`——该变量由 `mk/test.mk` 以 `-e "ghc_compiler_always_flags=
   '$(TEST_HC_OPTS)'"` 预注入（`RUNTEST_OPTS`），绕不过去；
4. **驱动依赖**：`boilerplate.mk` 对 `ghc-pkg`/`hsc2hs`/`hp2ps`/`hpc` 是**硬要求**
   （缺一即 `$(error Cannot find …)`），haddock 可选——bindist 的 `bin/` 齐备才能跑；
5. **噪音**：`fatal: not a git repository …` 来自 perf 基线检查，可忽略；若想消掉，
   在树里 `git init` 一个空仓；
6. **实测边界（大样本，92 批 / 77 分组）**：执行位修复（shim 签名段保留 x 位）
   后按分类分批 `make test TEST="<名字…>"` 真跑——尝试用例定义 9,712
   （testsuite 包 10,070 的 96.5%），执行用例实例 10,167，通过 7,999（78.7%）。
   **非解释器依赖类 8,557 执行 / 7,911 过 = 92.5%**（typecheck 98.0%、
   indexed-types 98.1%、codeGen 99.7%、module 100%、deriving 99.6%）；
   **解释器依赖类（th/ghci/ghc-e/debugger/printer）仅 5.5%**——GHCi 需要
   libffi 可执行闭包，OHOS 禁可执行匿名内存（W^X），结构性不可用。未尝试：
   rts 325（缺陷 4）+ cabal 33（超时）+ sdist 库测试 299（需源码树构建态）。

## 七、大产物取数：分片下载 + 官方校验（避免"下完才发现坏"）

`downloads.haskell.org` 单连接限速（实测 ~20-60 KB/s）且会中途断流：

- 24–32 分片 HTTP `Range` 并行 + 每片**核对 `Content-Range` 与长度**再落盘；
- 服务器无视 Range 直接回 `200 + 整包`时要能识别并整体采用；
- **必须**与官方 `SHA256SUMS` 对账（本轮 33 MB 源码包与 7.8 MB testsuite 包
  都校验通过）；校验失败的常见原因是"某分片线程还没落盘就被中止"
  （表现为 `lzma: Corrupt input data`）——所以别在下载中途 kill，或 kill 后重下。

## 八、可直接引用的一页判据

| 症状 | 真因 | 处置 |
|---|---|---|
| `can't execute: Permission denied` / exit 126，产物 0660 | 新链接产物无执行位（缺陷 1） | chmod 755；不行则复制副本再 chmod；配方侧在签名 shim 保持执行位 |
| `TypeError: can't concat str to bytes`（任意命令） | `os.popen()` 平台缺陷（缺陷 2） | 改 `subprocess`；上游脚本的探测调用加守卫 |
| `curl: (60) SSL certificate …` 且 http_code 000 | 本机 CA 库损坏（缺陷 3） | 改用 python urllib（unverified ctx）复核 |
| `NameError: name 'ghc_compiler_always_flags' is not defined` | 绕过 make 直调 testsuite 驱动 | 走 `make test TEST=…`，让 `mk/test.mk` 完成 `-e` 预注入 |
| `could not execute: gcc`（ghc 内部） | 子进程 PATH 丢了包的 `bin` 前缀 | `PATH = <pkg>/bin + ":" + PATH`（不要 setdefault） |
| `lzma: Corrupt input data` | 分片下载有空洞/坏片 | 重下并与官方 SHA256SUMS 对账 |
| 作业无声消失、终端同被关、全局内存充足 | 终端 hishell 会话的 memory cgroup 被内存压测打爆，整组清杀（缺陷 4） | `/proc/self/cgroup` 确认；该类测试整类排除或移出终端 cgroup |
| `make -n test` 真的跑了全量测试 | test 目标 recipe 以 `+` 开头，GNU make 对带 `+` 的行即使 -n 也执行 | 抓驱动配置行用 `make -n` 前先确认目标 recipe 无 `+`；或直接用 `make test TEST=<名字…>` |
| 驱动直调报 `can't open file '…/../driver/runtests.py'` | 驱动脚本是相对路径，cwd 不对 | 必须以 `testsuite/tests/` 为 cwd 执行 |
