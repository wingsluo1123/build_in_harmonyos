# yatas 1.6.1 — 适配笔记

## 基本信息
- **适配状态**: built
- **适配版本**: 1.6.1
- **用户名**: m0_66826439
- **队伍**: NebulaAGI
- **构建系统**: conan2 + go1.26.5
- **语言**: Go（纯 Go CLI，CGO_ENABLED=0）

## 本轮（真机预检修复，fixing_verification）

### 真机失败现象（hmbs-preflight 2026-09-29）
conan create 退出码 1。日志含两条关键链条：
1. `go test -v -count=1 ./...` 只打印 `FAIL`，无任何 `--- PASS:`/`--- FAIL:`/`--- SKIP:`
   → 上游标记 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,...}`。
   但 yatas 1.6.1 官方 tarball 有 11 个 *_test.go / 48 个顶层 Go 测试（linux 本机实测全部 PASS）。
2. test_package `test.sh` 在第 3 步 `--help` 核心 flag 检查失败 → test() 抛 ConanException
   Error 1。

### 根因
- **上游 go test 失败根因**：OHOS 上每个被执行 ELF 都需带 `.codesign` 签名。主线
  `go build .` 在 ext2 工作区（/data/storage/el2/base/haps/entry/files/…）链接并经
  `_sign_elf_if_ohos` 签名后能跑（test_package 里 `--help` 正常输出）。但
  `go test ./...` 会为每个包链接出一个 *测试二进制* 并 fork/exec；这些测试二进制
  未签名，OHOS 内核拒绝执行 → `go test` 报 `FAIL <pkg>` 且零 PASS 行 →
  discovered:0 / status:no_tests。佐证：同源的 aiac Go 配方（无 *_test.go，go test
  只报 `[no test files]`，不 exec 测试二进制）可过预检；osv-scanner 配方亦用
  `-toolexec` 处理 OHOS ELF 签名/链接问题。本地 linux `go test ./...` 48 项全过，
  唯一差异即 OHOS 对未签名测试二进制的 exec 限制。
- **test.sh 第 3 步根因**：yatas 用 Go 标准 flag 包，`--help` usage 打印的是单横线
  flag（`-init` / `-readme` / `-install` …），而旧 grep 用 `--init|--readme`（双横线）
  永远不匹配 → test.sh 非零退出 → test() 失败。

### 修复（未 commit，工作树）
1. `conanfile.py` 增加 OHOS `-toolexec` 包装脚本 `_TOOLEXEC_LINK_SIGN`（模块级字符串）
   与 helper `_ohos_toolexec_args()`。wrapper 在 `link` 工具产出二进制后调用
   binary-sign-tool 自签名（幂等：已含 .codesign 则只 chmod）。`go build` 与
   `go test -v -count=1 ./...` 在 OHOS 上均带 `-toolexec`/签名处理器。
   - `build()`：`go build $(toolexec_str) -trimpath -ldflags="-s -w" -o …`
   - `_run_upstream_tests(go, toolexec_args=None)`：cmd 拼入 `-toolexec`，
     base_env 注入 `OHOS_BINARY_SIGN_TOOL`。
   - Linux（非 OHOS）toolexec 为空，行为不变。
2. `test_package/test.sh` 第 3 步 grep 改为匹配单横线 printed flag：
   `grep -qE -- "(-init|-readme|-install|-only-failure)"`（命令行仍接受 --init/--readme，
   仅 usage 文本是单横线）。
3. 同步更新 test_package/conanfile.py 与 MANIFEST.yml 的说明注释。

### 修复验证（linux 本机，非真机）
- 从官方 v1.6.1 源码 `go build` 出 yatas 二进制：
  - `yatas --help` usage 确认为单横线 flag（-init/-readme/-install/-only-failure…）。
  - `yatas --init` 退出 0 并生成非空 `.yatas.yml`。
  - 修改后的 test.sh 全部 5 步断言通过（rc=0）。
- `go test -v -count=1 ./...` 本地 48 项 `--- PASS:`，0 FAIL / 0 SKIP（go1.22 amd64）。
- `-toolexec` 包装脚本机制验证：`go test -toolexec <wrapper> -v -count=1 ./...`
  本地 48 项全过；wrapper 正确拦截 5 个测试包的 `link` 步骤（输出 "…test" 路径），
  linux 无 signer 时透传不签名；OHOS 有 signer 时会在 go exec 前完成签名。

### 真机口径
上游测试 48（go_test_functions，逐 *_test.go 盘点），真机 `go test -v -count=1 ./...`
应输出 48 PASS。HMBS_UPSTREAM_TEST_RESULT status 应为 passed、discovered/executed=48。
test_package 断言 5（HMBS_TEST_PACKAGE_RESULT discovered/passedCount=5），全部通过。
是否有效由下一次真机预检判定。


## 真机预检第 2 轮（fixing_verification，2026-09-29）

### 真机失败现象
test_package 5/5 通过（--help / --init / .yatas.yml 都正常，主程序签名可执行）。
但 build() 里的上游测试仍失败：`go test -toolexec .../toolexec_link_sign.py -v -count=1 ./...`
在真机输出只有裸 `FAIL\n`（subprocess 捕获的 stdout 首 2048 字符仅 "FAIL"），
零 `--- PASS:` 行 → HMBS_UPSTREAM_TEST_RESULT 仍 status=no_tests / discovered=0。
清单声明 upstream_tests_exist=true + 48，故证据门禁判 incomplete 拒绝放行。

### 根因
- Linux（go1.22）下 `go test -v -count=1 ./...` 精确输出 48 条非缩进 `--- PASS:`
  （48 个顶层测试函数，5 个含测试的包 3+1+8+34+2=48），配方旧解析逻辑正确；
  主程序 `go build` 经 toolexec+ext2 工作区+_sign_elf_if_ohos 也成功（test_package 通过）。
- 真机唯一差异即 OHOS `go test ./...` *driver* 不可靠：它要链接 5 个按包测试二进制，
  并经隐式 `go vet` + 多二进制并行 exec 路径，在 OHOS 的 ELF 签名 / fallocate(ext2 工作区)
  限制下直接整体崩溃成裸 "FAIL"，无按包细节（本地无法用 go1.22 复现该裸 FAIL，
  判定为 go1.26.5 + OHOS 特定 driver 行为）。
- 关键佐证：把测试二进制靠 toolexec 自签名再 exec 仍是走 `go test ./...` 这个脆弱
  driver，为此前方案失效点。

### 修复（未 commit，工作树）
重写 `conanfile.py::_run_upstream_tests`，放弃 `go test ./...` driver，改用「复用真机
已证实的机制」：
1) 用 `Path.rglob("*_test.go")` 发现 5 个含测试的包；
2) 对每包 `go test -c -o <ext2工作区>/test-bin/<slug>.test ./<pkg>` 在 ext2 工作区
   单次链接出测试二进制（无 driver、无 vet、无并行多二进制 exec）；
3) OHOS 上用与主程序完全相同的 `_sign_elf_if_ohos`（binary-sign-tool 自签名）签名
   每个测试二进制 —— 这正是被证实的可执行路径；
4) 以 cwd=<包目录> 直接执行每个测试二进制（等价 go test 的工作目录语义，相对
   fixture 能解析），解析非缩进 `--- PASS/F/SKIP:` 行。
聚合计数来自唯一确定性来源（真实测试二进制输出的顶层用例行），无减法/猜测；
真有包构建/运行失败时如实记 run_failures / gaps，不伪造 no_tests。

### 本地仿真验证（linux，非真机）
按新逻辑逐包 `go test -c -o ... -test.v -test.count=1`（cwd=包目录）：
internal/cli 3、internal/helpers 1、internal/report 8、plugins/commons 34、
plugins/logger 2 → 聚合 PASS=48 FAIL=0 SKIP=0，discovered=executed=48，run_failures=[]
与清单 48 一致。真机效果由下一次预检判定。

### 真机口径
上游测试 48（go_test_functions 不变），真机预计 HMBS_UPSTREAM_TEST_RESULT status=passed、
discovered/executed=passed=48。test_package 5/5。是否有效由下一次真机预检判定。


## 本轮（CI 修复，fixing_ci，2026-09-29）

### CI 失败现象（build #64847，worker CI-040）
conan create 的 build() 阶段：上游 48/48 Go 测试在真机 CI-040 全部通过
（HMBS_UPSTREAM_TEST_RESULT passed/discovered/executed=48），主程序 go build 成功，
Package built。但紧接着 test_package 的 test.sh 在第 2 步 exec 打包出的 yatas 时报：
`test.sh[32]: .../p/bin/yatas: Operation not permitted` → conan create 失败。
CI harness 把类别判为「网络问题」（pre-download 阶段 `curl` 不存在只是 WARN，
非根因），但真正的硬失败是 test_package 对打包二进制 exec 被拒。

### 根因
- 上游测试二进制在 build() 里通过 `go test -c` 链接到 **ext2 可写工作区**
  （/data/storage/.../test-bin）并自签名后执行 → 在 CI-040 上能正常 exec
  （48/48 通过，缺证据显示签名工具在位）。
- 主程序 yatas 二进制在 build() 里被签名后放进 build_folder/package_folder，而
  conan 缓存目录（/storage/Users/currentUser/.cache/conan2/...）在 CI-040 上被挂载为
  noexec → test_package 直接 exec 缓存里的 p/bin/yatas 报 `Operation not permitted`。
- HMBS 预检机器 conan 缓存可 exec，故当前 head 在 HMBS 通过；CI-040 的 noexec 缓存
  是两者差异点（也正因如此配方才要把 GOCACHE/GOTMPDIR/link-out 重定向到 ext2 工作区）。

### 修复（未 commit，工作树）
- test_package/test.sh：在 exec 打包二进制前解析可执行副本——先直接 try 打包路径
  （正常可 exec 文件系统上行为不变）；若 exec 返回权限类错误，则把二进制做字节复制到
  当前可写工作目录（HMBS 注入的 TMPDIR，test.sh 已 cd 到那里），chmod 755 后使用
  副本执行（保留 .codesign，OHOS 可 exec）。整个脚本改用 RUN_BIN 变量。
- 同步更新 test_package/conanfile.py 顶部 docstring 说明;断言数仍为 5（口径不变）。
- HMBS 预检路径保持「先直跑原路径」→ 在 HMBS 上 RUN_BIN 即原路径，行为不变，仍应通过。

### 待验证
是否修复下一轮 CI（worker CI-040 若 TMPDIR 可 exec 则应通过；若 TMPDIR 亦 noexec
则需改用 /data/storage ext2 工作区作为复制目标，本轮无法确定）。上/下游测试口径不变。



## 本轮（CI 修复，fixing_ci，2026-10-12）

### CI 失败现象（build #87320，worker CI-005）
build() 阶段主程序 `go build` 一开始即失败：
`go: error obtaining buildID for go tool compile: fork/exec
 /data/storage/.../yatas-1.6.1-go/toolexec_link_sign.py: resource temporarily
 unavailable`（EAGAIN）。pre-download 阶段 `curl` 不存在只是 WARN，非根因；真机
（HMBS）此前同 head 通过，CI worker 与 HMBS 的差异触发此错误。

### 根因
`-toolexec` 会把每个 Go 构建工具（compile/asm/vet/link/…）都经包装脚本 fork/exec
一次，且 `go build` 对每个依赖包并行起一个工具、并行度=NumCPU。旧包装脚本是
`#!/usr/bin/env python3`，且内部再 `subprocess.call([tool]+args)` 派生一个子进程
——每个并行工具 = 1 个 python 包装 + 1 个子进程，进程数翻倍。高核数 CI worker 上
并发峰值瞬间打满每用户进程/线程上限（RLIMIT_NPROC/线程），`fork/exec` 返回 EAGAIN，
go 在探测 compile 工具 buildID 时抛出上述错误。HMBS 真机核数/进程上限较宽裕故通过。

### 修复（未 commit，工作树）
conanfile.py：
1. `-toolexec` 包装脚本由 python3 换成轻量 **bash**（`#!/data/service/hnp/bin/bash`，
   与已验证的 osv-scanner 配方同款解释器）：非 link 工具直接 `exec "$TOOL" "$@"`
   （零额外子进程，不再派生 python）；仅单个唯一的 `link` 步骤在产出后原位自签名。
   每次构建只有一个 link，用固定 tmp 目录（进入时先 rm -rf）即可，无并发冲突。
2. 新增 `_go_build_parallel_flag()`：OHOS 上给 `go build`/`go test -c` 加 `-p 4`，
   把并行工具数上限压到 4，从根上阻止「NumCPU 个并发包装进程」打满进程/线程上限。
   正确性不受影响，仅墙钟速度变慢。
3. 包装脚本文件名改为 `toolexec_link_sign.sh`（`_ohos_toolexec_args` 同步）。

非 OHOS（Linux）`_ohos_toolexec_args=[]`、`_go_build_parallel_flag=""`，行为不变。
上游 48 / test_package 5 口径不变。

### 本地验证（非真机）
- Python AST 解析 OK、内嵌 bash 包装脚本 `bash -n` 语法 OK。
- 逻辑仿真：compile（非 link）被直接 exec 且不触发 signer；link 运行后对 -o 输出
  成功调用签名流程。OHOS 真机效果由下一次预检判定。

### 待验证
上一轮 test_package noexec 问题（CI-040）已由 RUN_BIN 可写副本兜底修复；本轮处理
独立的新 EAGAIN。是否真正通过由下一次真机预检 + CI 判定。

## 本轮（真机修复，fixing_verification，2026-10-12 head 5febe5f）

### 真机失败现象
预检 failed：compile 阶段上游测试与 test_package 双双失败。
1. 上游测试：5 个包全部 `GO TEST -c ... FAILED (no test binary)`，报
   `go: unknown flag -p 4 cannot be used with -c`（discovered=48 executed=0）。
2. test_package：`yatas --help` exit 126 `Operation not permitted`，即使按
   test.sh 兜底把二进制字节拷贝到可写 TMPDIR 后 exec 仍被拒绝（非 noexec 挂载问题，
   是 OHOS XPM 对已带 .codesign 段的 ELF 拒绝加载）。

### 根因
1. 上一轮为缓解 EAGAIN 给 OHOS 加了 `_go_build_parallel_flag()` 并把它误用于
   `go test -c`。但 Go 明确规定 `-p` 不能与 `-c` 一起用（`-p` 只给 go build/run），
   于是 `go test -c` 全部报未知 flag、无测试二进制产出，48 个上游用例 0 执行。
   `-p` 只在 `go build` 阶段为压缩 toolexec 并发而需要。
2. 主程序 `go build` 通过 `-toolexec` bash 包装在 link 后原位写入 .codesign；
   build() 里 `_sign_elf_if_ohos(linked_exe)` 因检测到已有 .codesign 而 early-return，
   未用经 aiac 配方验证过的 Python 签名路径重新过签。该原位(toolexec)签名被后续
   test_package exec 时按 XPM 拒绝（exit 126）。类 DRAFT-14257 原则：过期/早期写入的
   .codesign 需在投入使用前移除并用可信 signer 重签。

### 修复（未 commit，工作树）
conanfile.py：
1. `_run_upstream_tests` 中 `go test -c` 一律不再注入 `-p` 标志（去掉 pflag 分支），
   仅保留 `[go, "test", "-c", "-o", <test_bin>, <pkg>]`；`-p` 仅由 `_go_build_parallel_flag()`
   在 `go build`（主程序）应用。
2. `_sign_elf_if_ohos(path, force=False)` 增加 force 参数；force=True 时无条件
   `llvm-objcopy --remove-section .codesign` 后再用 binary-sign-tool 重签
   （即先剥掉早期 toolexec 写的签名，再以 aiac 同款可信路径重签）。
3. build() 对主程序改为 `self._sign_elf_if_ohos(linked_exe, force=True)`，确保打进
   包的 bin/yatas 携带有效的 .codesign，test_package exec 不再 126。

### 本地验证（非真机）
- Python AST 解析 OK。
- 逻辑核对：`go test -c` 不再带 -p；主程序 build 后强制重签；osv-scanner/aiac 同类
  bash-toolexec + python-重签路径已被 prior 顶层验证过。OHOS 真机效果由下一次预检判定。

### 待验证
下一次 hmbs 真机预检：期望上游 48 测试全跑(executed=48)，test_package 5/5 且 --help/--init
正常，不再 126。


## 本轮（CI 修复，fixing_ci，2026-10-15 复盘 build #88310）

### CI 失败现象（build #88310，worker CI-039，head eb4c0574）
conan-build-test 步骤在**脚本最前端的 G0 知识图谱门禁**处即失败：
```
eci/conan/build_and_test.sh:116: resource temporarily unavailable: grep
eci/conan/build_and_test.sh:133: resource temporarily unavailable: wc
hprogram finished with exit code 127
```
G0 运行于任何包构建之前（仅对 knowledge/graph 做完整性统计），尚未进入 conan create，
yatas 配方代码完全没有开始执行。

### 根因
CI worker（CI-039）瞬时进程/线程资源耗尽：连 `grep`/`wc` 都无法 fork（EAGAIN →
zsh 报 "resource temporarily unavailable: <cmd>"，退出 127）。属 **Worker 基础设施/瞬时负载**
故障（同类：DRAFT-11327 `can't fork`/`Resource temporarily unavailable`，失败点落在 CI 自身
脚本而非目标包）。同 head 真机预检已通过（上游 48/48 + test_package 5/5）；该 G0 步骤与包
内容无关——PR 仅改动 archives/y/yatas/* 共 10 个文件，未触碰 knowledge/。对照前一轮 CI-005
build #87320：G0 正常通过（546 entries），说明 G0 本身无结构性缺陷；88310 是 worker 瞬时故障。

### 处置（未 commit，工作树仅 notes.md 记录）
- 未修改 conanfile.py/test.sh/任何配方：失败点在配方运行之前，配方无法、也不应"修复"worker
  的 fork 能力；禁止把环境失败当作配方缺陷处理（DRAFT-11327 forbid_1）。
- 未发送 /rebuild、未空提交：按规则由后端停留，等待 worker 资源恢复后重试。

### 待验证
下一次 CI（worker 资源正常时）对同 head eb4c0574 重跑：应过 G0 → L0（commands.json 已由
build #87320 验证有效）→ conan create（真机已通过）→ L1/L2/L4/L5。
