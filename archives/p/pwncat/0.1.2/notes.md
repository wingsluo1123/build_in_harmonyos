# pwncat 0.1.2 适配笔记

## 编译环境

- 类型：纯 Python 单文件 CLI（noarch），Conan `package_type = application` 配方
- 适配日期：2026-10-15
- Python：3.12.8（OHOS 运行时，`sys.version_info[:3] == (3, 12, 8)`）
- 平台：OHOS aarch64（`platform.system() == "HarmonyOS"`、`platform.machine() == "aarch64"`）
- Conan：2.29.1（OHOS 适配版）
- 最终状态：built

## 编译步骤

```bash
conan create archives/p/pwncat/0.1.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

```text
pwncat/0.1.2: Calling build()
pwncat/0.1.2: RUN: '…/python3.12' '…/bin/pwncat' --version
pwncat: Version 0.1.2 (https://github.com/cytopia/pwncat) by cytopia
pwncat/0.1.2: RUN: '…/python3.12' '…/bin/pwncat' --help
usage: pwncat [options] hostname port
…
pwncat/0.1.2: package(): Packaged 1 file: pwncat
pwncat/0.1.2: Full package reference: pwncat/0.1.2#19f30a3f…:d3de22f79f2e…  (conan-verify: @ohpcd/stable)
```

`pwncat` 只有一个产物：上游 `setup.py` 声明 `scripts=["bin/pwncat"]`、`install_requires=[]`，
没有可导入包、没有 C/C++ 扩展、也不调用 setuptools/pip 构建后端。因此配方是「装脚本」：
`source()` 取官方 PyPI sdist → `build()` 校验 shebang 并**实跑** `--version`/`--help`（解释型应用的"编译"就是
证明脚本在本解释器下能解析并跑起来）→ `package()` 把 `bin/pwncat` 落盘到 `bin/`、`chmod 755`。
`package_info()` 只声明 `bindirs=["bin"]`（另需 commands.json，R38）。

## 依赖预检（W0/R36）

```bash
bash ci/scripts/preflight_check.sh pwncat/0.1.2
# [INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。
# [OK] 预检通过（无依赖需要检查）
```

| 依赖 | 状态 |
|------|------|
| 运行时 | **无** —— PyPI `requires_dist: null`、`setup.py` `install_requires=[]`、`requirements.txt` 为空文件 |
| 构建 | 无 |

零依赖 ⇒ 无 `requires()`、无需要先发布的依赖、无站点包 staging、无 `PYTHONPATH` 注入（R36 天然满足）。

## 上游测试清点与实测（R51 三步法）

### ① 清点（申报表，详见 `reports/test-report.md` §3）

| 上游入口 | 构成 | 用例数 |
|---------|------|-------|
| `make test` → `__test-*` | `tests/integration/**/*.sh`（bash 集成套件，`tests/.lib/conf.sh` 驱动） | **72 脚本 / 547 轮** |
| `make smoke` | `tests/smoke/{200,201,300,301,302,303}` docker-compose 用例 | 6 × 5 遍 |
| `make code-*` | docker 镜像 `cytopia/*` 静态检查 | 5 目标 |

> pwncat **无** pytest/ctest 用例：`tests/` 下除 `README.md` 与 `.lib/conf.sh` 外没有 Python 测试文件，
> 也没有 `setup.cfg`/`pyproject.toml` 的测试入口；上游 CI 即按 `make __test-*` 逐条执行。

### ② 在可运行环境实跑

在 OHOS aarch64 运行时上以 **GitHub tag `v0.1.2` 完整源码树**逐脚本执行（等价上游 Makefile 默认
`HOST=localhost PORT=4444 WAIT=2 RUNS=1`），需两个**仅测试期**环境 shim（均不改上游文件）：

1. `ps` shim：toybox `ps` 拒绝 BSD `auxw`（且 `-A` 截断 CMD），上游用 `ps auxw | … | awk '{print $2}'` 轮询进程 → 归一为 `-ef`。
2. `sitecustomize.py`：运行时 `/etc/hosts` 缺 `::1 localhost`（`getaddrinfo("localhost",…,AF_INET6)` 报 gaierror），
   上游 CI **自己就是** `sudo tee /etc/hosts` 补这一行；OHOS 上 `/etc/hosts` 不可写且无 sudo/unshare，故在解析层补
   （并尊重 `AI_NUMERICHOST`，不改变 `--nodns` 语义）。

### ③ 实测回填

| 指标 | 实测 |
|------|------|
| 脚本 | **63 / 72 通过** |
| 轮次 | **515 / 547 已执行**，其中 **506 通过** |
| 失败 | 9 个脚本，全部为环境 / harness 原因，非 pwncat 缺陷 |

未执行说明：6 个脚本（`01/200`、`01/201`、`03/000`、`03/001`、`10/000`、`11/000`）在**第 1 轮**即因
`set -e` 中止（未执行其剩余变异，合计 32 轮）。失败脚本按根因分三类：

| 根因 | 脚本 | 证据 |
|------|------|------|
| 硬编码 `www.google.com:80`，需出网 | `01/200`、`01/201`、`10/000`、`11/000` | `curl http://www.google.com/` → `(52) Empty reply from server`、`http=000`；机制已用本地 HTTP/1.1 keep-alive 服务替代验证通过 |
| harness `grep -E 'FATAL\|ERROR'` 误报 | `03/000`、`03/001` | `-vvvv` 下 pwncat 把载荷 `TRACE` 到 stderr，OHOS `/bin/ls`（toybox）内嵌字面量 `ERROR :Range for -f is 1 to %ld`；传输本体实测 609024 B 逐字节一致（sha256 相同、rc=0） |
| CnC self-inject 与 `revshell.py` 替身握手失败 | `30/001`、`30/002`、`30/004` | `001`/`002` 报 pwncat 自身日志 `[PWNCAT CnC] Unable to create tmpfile. Aborting and handing over to current shell.`；`004` 因单字节+延迟（上游 `TRIES=600`）轮询耗尽仍未完成握手。**同注入通路在 `30/000`（对端为 pwncat）与 `30/003` 上通过**，且 `bin/pwncat` 无硬编码 `/tmp`、本环境 `tempfile.mkstemp()` 正常 → 判定为测试替身交互问题，不改源码 |

不可运行：6 个 docker 冒烟用例 + 5 个 docker 静态检查目标（本环境无 `docker`/`docker-compose`/`podman`/`nerdctl`，
且冒烟镜像为 x86_64/glibc alpine）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | `30-cnc---self_inject/000` 报 `Inject shell is not running` | OHOS 的 toybox `ps` 拒绝 BSD 语法 `ps auxw`（`bad auxw`），测试的 80 次轮询永远失败——尽管注入进程确实在跑 | 测试期 `PATH` 前置 `ps` shim，把 `auxw`/`aux` 归一为 `-ef`；重跑 **rc=0**（`-ef` 第 2 列即 PID、CMD 完整，满足上游 `awk '{print $2}'` 与 `grep reconn-wait`） |
| 2 | `01-*` 全部在第 3 个变异（客户端 `-6`）失败，日志 `Resolving IPv6 host: localhost failed` | 运行时 `/etc/hosts` 缺 `::1 localhost`（只有 `ip6-localhost`/`ip6-loopback`）；`getaddrinfo("localhost",…,AF_INET6)` → gaierror。字面量 `::1` 正常，能 bind/connect | 测试期 `PYTHONPATH` 注入 `sitecustomize.py`：仅当报 gaierror 且主机名是 localhost 时，用 `/etc/hosts` 已有的 `ip6-localhost` 重试；**`AI_NUMERICHOST` 时不做回退**（保住 `--nodns` 语义）。这不是自创补丁——上游 CI 正是靠写 `/etc/hosts` 补 `::1 localhost` |
| 3 | `03-behaviour-base--file_transfer/{000,001}` 报「Client has errors」 | 测试以 `-vvvv` 运行，pwncat 会把收发载荷 `TRACE` 到 stderr（`Received: b'…'`），而 OHOS 的 `/bin/ls`（toybox 多元二进制）内嵌字面量 `ERROR :Range for -f is 1 to %ld (max ttl)` → 触发 harness 的 `grep -E 'FATAL\|ERROR'` 误报 | **非 pwncat 问题**：实测传输本体逐字节一致（609024 B，sha256 相同，rc=0）；已在报告中如实记录为 harness 误报（GNU coreutils 的 `/bin/ls` 不含该串，故上游 CI 不命中） |
| 4 | `01/200`、`01/201`、`10/000`、`11/000` 失败 | 4 个脚本**硬编码** `www.google.com:80`（不取命令行参数），需要出网；本环境不可达（`curl http://www.google.com/` → `(52) Empty reply from server`, `http=000`） | 无法在本环境消除；用**本地 HTTP 服务替代验证**证明机制在 OHOS 上正常：`01/200` 等价场景（HTTP/1.1 keep-alive）收到 `Set-Cookie:` 且客户端保持存活；`10/000` 等价场景经本地转发取回 `Set-Cookie:` 与响应体 |
| 5 | `conan-verify` G1 报「缺少 export_sources() 方法 / 补丁应用调用」 | G1 是**字面子串**检查，要求配方具备标准形状；本包零补丁故初版未写 | 补上 `export_sources()`/`apply_conandata_patches()`（`conandata.yml` 无 `patches` 键 ⇒ 二者均为 no-op，Conan 会打印 "No patches defined in conandata"）；**不虚构补丁**，`patches_applied: []` 保持为空 |
| 6 | `30-cnc---self_inject/{001,002,004}` 报 `Inject shell is not running` | pwncat 自身日志为 `[PWNCAT CnC] Unable to create tmpfile. Aborting and handing over to current shell.`（`001`/`002`）；`004` 则是在单字节+0.1s 延迟替身下（上游 `TRIES=600`）轮询耗尽仍未完成握手。5 个变体的服务端命令完全相同，差别只在反向 shell 对端 | **不改源码**：同注入通路在 `000`（对端为 pwncat 自身）与 `003`（多字节+0.5s 延迟）上跑通；`bin/pwncat` 无硬编码 `/tmp`（`grep '"/tmp\|/tmp/'` 无命中），本环境 `tempfile.mkstemp()` 亦正常，故属 `revshell.py` 测试替身「逐字节发送+banner/suffix」与 CnC 响应解析的交互问题，非 OHOS 可移植性缺陷 |

## 源码修改

**无。** 不创建 `patches/` 目录，`conandata.yml` 无 `patches` 段，`patches_applied: []`。

`bin/pwncat` 是仅标准库的纯 Python 3 脚本，未使用 `ps`/`/proc` 等平台特定接口，
在 OHOS aarch64 运行时上**原样**通过上游集成套件（见上表 #1~#4，所有差异都在测试侧或环境侧）。
`package()` 也**不重写 shebang** —— 上游 `bin/pwncat` 本就是 `#!/usr/bin/env python3`（`build()` 会断言这点）。

## 验证结果

### 上游测试（OHOS aarch64，Python 3.12.8）

```text
脚本 : 63 / 72 通过
轮次 : 515 / 547 已执行（506 通过）
失败 : 9（4 个硬编码 www.google.com:80 需外网；2 个 harness grep ERROR 误报；
          3 个 CnC self-inject 与 revshell.py 替身握手失败，同通路在 000/003 通过）
```

逐目录明细与失败证据见 `reports/test-report.md`；raw 日志为适配期 `$TMPDIR/pwncat-tests/logs/`。

> 值得强调的通过项：`02-behaviour-quit--server` 11/11、`21-options---crlf` 24/24（上游仅对 Windows 关闭该组）、
> `22-options---keep_open` 8/8、`23-options---reconn` 3/3、`30-cnc---self_inject/000`（`--self-inject` 全链路）、
> `20-options---nodns` 4/4。

### Conan 打包与消费者测试

```text
$ conan create archives/p/pwncat/0.1.2 -pr:h=… -pr:b=… --build=missing
pwncat/0.1.2: package(): Packaged 1 file: pwncat
======== Launching test_package ========
pwncat/0.1.2 (test package): RUN: python3 test_pwncat.py '<pkg>'
OK: pwncat 0.1.2 consumer test passed
pwncat/0.1.2 (test package): RUN: python3 test_pwncat_ohos.py '<pkg>'
OK: pwncat OHOS consumer test passed (system=HarmonyOS, machine=aarch64)
```

### conan-verify（五级门禁）

```text
✅ G1 PASS（配方完整性）   ✅ G2 PASS（干净 conan create）
✅ G3 PASS（R26 系统同名库隔离：无 lib/，纯可执行包）
✅ G4 PASS   报告: archives/p/pwncat/0.1.2/reports/conan-verify-report.md
```

### 打包入口

```text
$ <pkg>/bin/pwncat --version
pwncat: Version 0.1.2 (https://github.com/cytopia/pwncat) by cytopia
$ <pkg>/bin/pwncat --help        # 列出全部模式：-l/-z/-L/-R/--self-inject …
```

## 注意事项

- 本包只安装 `bin/pwncat`（对应上游 `scripts=["bin/pwncat"]`）；上游 man 页与 docs 不在 PyPI sdist 内，
  故未打包（上游 `setup.py` 也未声明 `data_files`，`pip install pwncat` 同样不装 man 页）。
- `python3.12` 下上游 `threading.Thread.getName()` 会打印一条 `DeprecationWarning`（`bin/pwncat:4210`），
  纯提示、不影响功能，未做修改。
- 运行时 `/etc/hosts` 无 `::1 localhost`：以**主机名**访问 IPv6 回环需用 `ip6-localhost`，
  或直接用字面量 `::1`（`pwncat -6 ::1 <port>` 正常）。`--nodns`（`-n`）下对主机名会给出受控
  `Resolve Error`（无 Traceback）。
- OHOS 的 IPv4 DNS 对不存在的域名会返回 `198.18.0.x` 通配结果（本环境解析器行为），
  故 `pwncat <不存在的域名> <port>` 会尝试连接该地址而非报解析错误；与本包适配无关，仅记录。

---

**适配结束**: 2026-10-15
**最终状态**: built
---

**编译结束**: 2026-10-16 01:41
**最终状态**: built
