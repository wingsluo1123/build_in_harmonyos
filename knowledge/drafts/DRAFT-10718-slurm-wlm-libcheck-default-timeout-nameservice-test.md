# DRAFT-10718：libcheck 的 4 秒默认超时会把「真去调用名字服务」的上游用例判成失败

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-14
> Source: slurm-wlm 25.11.4 HarmonyOS PC 适配（`archives/s/slurm-wlm/25.11.4`）
> 对应：`knowledge/drafts/DRAFT-10718-slurm-wlm-libcheck-default-timeout-nameservice-test.kv`
> 相关：DRAFT-E547（libcheck 临时目录 P_tmpdir 优先）、DRAFT-E571（libcheck 先探测 TEMP）、
> DRAFT-10251（上游测试套件被 configure 守卫静默排除）

## 现象

在 HarmonyOS PC 上跑 slurm 25.11.4 的上游单元测试套件（`testsuite/slurm_unit`，Check/libcheck 驱动，
共 41 个用例，通过 `make check` 执行），40 条用例都正常，只有 DNS 相关的那条稳定失败：

```text
Running suite(s): dns
0%: Checks: 1, Failures: 0, Errors: 1
.../testsuite/slurm_unit/common/dns-test.c:61:E:dns:test_dns:0: (after this point) Test timeout expired
FAIL dns-test (exit status: 1)
```

注意失败列是 **Errors**（不是 Failures），错误文本是 **Test timeout expired** —— 这两点是把
「框架运行参数问题」与「断言失败（真 bug）」区分开的第一手信号。

## 根因

libcheck 对**每个用例**有一个默认 4000 ms 的超时（环境变量 `CK_DEFAULT_TIMEOUT`，未设置时用内部默认），
到点由 check 自己的 fork 监控上报 `Test timeout expired`，进程以非 0 退出。

而这条用例并不是纯计算：`dns-test.c` 通过被测代码 `sockaddr_to_string()` → `getnameinfo()`
去解析地址的**名字**（回环地址、`AF_UNSPEC` 的零地址等，前置一次 `getnameinfo_cache_purge()`）。
当机器上的解析器不可达时，这一次调用要等解析器自己的超时/重试（数秒）才返回 —— 于是 > 4 s。
代码路径本身完全正常。

**对照组证据**（同一二进制、同一台机器、只改超时）：

```sh
$ (cd <build>/testsuite/slurm_unit/common && ./dns-test)
0%: Checks: 1, Failures: 0, Errors: 1            # 默认 4 s

$ (cd <build>/testsuite/slurm_unit/common && CK_DEFAULT_TIMEOUT=120 ./dns-test)
100%: Checks: 1, Failures: 0, Errors: 0          # 120 s
```

所以这条失败属于**测试框架计时参数与运行环境的组合**，不是适配缺陷、也不是上游代码缺陷。

## 与「另一个 libcheck 环境坑」的区别

check 还有一类非常像的环境问题，容易被混为一谈：

libcheck 选择 fork 通信临时文件的顺序是 `TEMP` → `P_tmpdir`（musl 里定义为 `P_tmpdir="/tmp"`）→ `TMPDIR`。
设备上 `/tmp` 是 root 拥有、普通用户只读，于是**所有**用例一起报：

```text
.../check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
```

（该问题已有条目：DRAFT-E547 / DRAFT-E571，处置是把 `TEMP` 指向构建目录下的可写目录。）

| 现象 | 触发点 | 判别特征 | 处置 |
|------|--------|----------|------|
| `Unable to create temporary file for communication` | 临时目录不可写 | **全部**用例一起失败 | 设 `TEMP=<build>/check-tmp` |
| `Test timeout expired` | 解析器/网络不可达 | **个别**用例（名字服务相关）失败，Errors 列 +1 | 设 `CK_DEFAULT_TIMEOUT=120` |

两类都是"环境"，但一个写不出文件、一个等网络超时；改错方向会白跑几轮。

## 判定流程（先分类，再处置）

```sh
# 1) 失败面分类：assertion 失败 vs 框架报错
grep -n "Test timeout expired" testsuite/**/*.log
grep -n "check_msg.c:"         testsuite/**/*.log

# 2) 单跑对照：默认超时 vs 放大超时
(cd <build>/testsuite/slurm_unit/common && ./dns-test)
(cd <build>/testsuite/slurm_unit/common && CK_DEFAULT_TIMEOUT=120 ./dns-test)

# 3) 整树重跑（不要只跑单条）
make -k check CK_DEFAULT_TIMEOUT=120
```

## 处置（配方侧固定 libcheck 运行环境）

```python
    def _run_upstream_tests(self):
        tmp = os.path.join(self.build_folder, "check-tmp")
        os.makedirs(tmp, exist_ok=True)
        os.environ["TEMP"] = tmp                    # 见 DRAFT-E547/E571
        os.environ["CK_DEFAULT_TIMEOUT"] = "120"    # 4 s 对名字服务型用例太短
        self.run("make -j1 -k check", env="conanbuild", cwd=self.build_folder,
                 ignore_errors=True)
```

报告/PR 里必须把这类失败**单独归类**为"框架计时/运行环境"，并附对照组证据 —— 这样
R51「逐项列出具体技术原因」才站得住。

## 不要做的事

- 不要为了让它变绿去改上游测试源码（超时是框架侧参数，改源码等于篡改上游用例）；
- 不要把该用例从 `TESTS` 里删掉（会掩盖真实通过率，属 R51 如实回填失守）；
- 不要在整树里只补跑这一条用例来"凑通过率"，要么整树重跑，要么如实记录。

## 通用化建议

1. 看到 `make check` 里出现 `Test timeout expired`，先当成**计时问题**排查，而不是先怀疑平台不兼容。
2. 任何"上游用例通过率不是 100%"的复核，都先做失败面分类：断言失败 / 框架环境 / 依赖未接 /
   环境数据缺失。分类清楚再决定是补依赖、调框架参数，还是写豁免。
3. libcheck 场景下的两个环境变量值得默认固定：`TEMP`（可写临时目录）与 `CK_DEFAULT_TIMEOUT`（放宽超时）。
