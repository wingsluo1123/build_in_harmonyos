# swaks 20240103.0 适配笔记

## 编译环境

- 构建系统: custom（单文件 Perl 脚本，无构建系统、无编译步骤）
- 适配日期: 2026-10-15
- 编译器: 不涉及（`conan create` 只做源码校验与打包）
- 状态: built（真机 shadow CI 单包验证通过，未 upload）

## 源码与产物

| 项目 | 值 |
|------|-----|
| 上游仓库 | https://github.com/jetmore/swaks |
| 上游主页 | https://jetmore.org/john/code/swaks/ |
| 发布资产 | `swaks-20240103.0.tar.gz`（121308 字节） |
| sha256 | `0e531b4d164058802e7266b14f4dc1897099d096f930820de2f9b5eb08dcdbe8` |
| 资产内容 | `swaks`、`README.txt`、`LICENSE.txt`、`doc/{Changes,recipes,ref}.txt` |
| 打包产物 | `bin/swaks`（244177 字节，0755）、`licenses/LICENSE.txt`、`share/doc/swaks/*.txt` |

官方源等价性（三方一致，sha256 完全相同）：

1. GitHub Release 资产 `https://github.com/jetmore/swaks/releases/download/v20240103.0/swaks-20240103.0.tar.gz`
2. 上游官网 `https://www.jetmore.org/john/code/swaks/files/swaks-20240103.0.tar.gz`
3. Homebrew 公式 `Formula/s/swaks.rb` 中记录的 `sha256`

`conandata.yml` 保留 GitHub 地址：CI 会为 `github.com` 自动追加 gh-proxy 镜像候选，真机首次构建正是
从 `https://gh-proxy.com/...` 取到源码（`Sources correctly downloaded from https://gh-proxy.com/...`），
sha256 校验保证镜像内容与官方一致。

## 构建步骤

`swaks` 没有 configure/CMake/Makefile，`conan create` 只做三件事：

1. `source()`：下载并解包官方发布资产。
2. `build()`：不做编译，改为校验身份——脚本内必须出现
   `build_version("20240103.0"`，且首行必须是 `#!/usr/bin/env perl`；任一不满足即 `ConanException`。
   真机日志：`source script verified (244177 bytes, upstream shebang kept)`。
3. `package()`：把 `swaks` 装到 `bin/`（0755），`LICENSE.txt` 装到 `licenses/`，
   `doc/*.txt` 与 `README.txt` 装到 `share/doc/swaks/`。

`package_info()` 只暴露 `bindirs=["bin"]`，并显式清空 `libdirs`/`includedirs`/`libs`，
避免这个纯 CLI 包被下游当作库消费。

`settings` 必须写全 `os, compiler, build_type, arch`（CI 门禁 L0p），不能照抄 acme.sh 的
`settings = "os", "arch"`。

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| perl | 5.42.2 | 运行时依赖（`run=True`） | 脚本解释器；ohpcd 上已有 OHOS 二进制包（17.0MB），真机 `conan create` 时自动下载 |

声明为 `run=True` 而不是 `tool_requires` 的理由：`run=True` 表示"目标机运行时需要的可执行文件/共享库/
数据"，Conan 的 `VirtualRunEnv` 只对 `run=True` 的依赖把 `cpp_info.bindirs` 追加进 `conanrun` 的
`PATH`（`conan/tools/env/virtualrunenv.py` 的 `if require.run:` 分支），而 `package_type="application"`
的包对下游默认 `run=True`。因此测试里 `swaks` 与 `perl` 都能在 `conanrun` 下被解析到，
"解释器依赖是否真的接上"成为可被测试证伪的事实，而不是假设。

### 脚本的 Perl 模块依赖（W0 的第二层检查）

只确认 `perl/5.42.2` 已发布还不够——脚本本身对模块有硬依赖。本次直接清点 ohpcd 上 OHOS perl 包
（`lib/perl5/5.42.2/`）并在真机复核：

- 编译期硬依赖：`use strict`、`use Pod::Usage`、`use File::Spec::Functions` → 全部存在。
- `--help` 渲染链路：`Pod::Text` / `Pod::Simple` / `Pod::Simple::Methody` / `Pod::Text::Termcap` /
  `Text::Tabs` / `Encode` → 全部存在（真机 `--help` 正常输出 POD）。
- 运行期按需加载：`IO::Socket::IP`（首选 socket 传输）、`IO::Socket::INET`/`UNIX`、`IPC::Open2`
  （`--pipe`）、`Sys::Hostname`、`POSIX`、`Time::HiRes`、`MIME::Base64`、`Digest::MD5`/`Digest::SHA`、
  `Net::Netrc` → 全部存在。
- 缺失（可选特性）：`Net::SSLeay`（TLS）、`Net::DNS`（MX 路由）、`Authen::NTLM`、`Authen::SASL`。
  真机 `swaks --support` 已如实报告 `TLS not available: requires Net::SSLeay`。
- `Pod::Usage` 文档里的 `use Pod::Find` 位于 `__END__` 之后的 POD 段（OHOS 包内 `Pod/Usage.pm`
  第 387 行 `__END__`、第 531 行才是文档示例），不是加载期依赖，不需要 Pod-Parser。
- 真机自查：`perl -MPod::Usage -e1 && perl -MIO::Socket::IP -e1 && perl -MIPC::Open2 -e1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **真机 CI L0p 失败**：`settings 缺少 'compiler' / 'build_type'` | 首版照抄仓库内纯脚本包 acme.sh 的 `settings = "os", "arch"`；当前 CI 的 L0p 门禁要求四项齐全，否则 `conan create` 前即拦截 | 改为 `settings = "os", "compiler", "build_type", "arch"`；本机 L0 仿真同步补齐 L0p/L0o/L0q 等新门禁 |
| 2 | 隔离 `CONAN_HOME` 下 `conan create` 报 `The 'profile.py' plugin file doesn't exist` | 新建的 conan-home 只复制了 settings.yml/profiles/remotes.json，没有 `extensions/plugins/` | 复制 `$HOME/.conan2/extensions` 到隔离 conan-home（不复制 `p/` 缓存，保持隔离） |
| 3 | L2 smoke 报告 `swaks --version/--help failed` | L2 以**环境 PATH**直接执行 `bin/swaks`，不激活 `conanrun`；设备上既无系统 perl，perl 自身也需要依赖包注入的 `PERL5LIB` | 结构性问题，非配方缺陷：CI 脚本已将 L2 标为 non-blocking；`--version`/`--help` 由 test_package 在 conanrun 下证明（rc=0），另做了独立的 run-env 手工复核 |
| 4 | 本机 perl 缺 `Pod::Usage`，`swaks` 无法启动 | Git for Windows 自带 perl 是裁剪版，删掉了 Pod::* 与 ExtUtils::* | 仅影响本机演练：临时把 CPAN 的 Pod-Usage/Pod-Simple/podlators/Pod-Escapes 放进 `PERL5LIB`；同时改为直接清点 OHOS perl 包，确认真机模块齐全 |
| 5 | `sources:` 写成 list 会让 `get(self, **self.conan_data["sources"])` 直接 TypeError | 仓库内 845 个配方用 dict 形式、6 个用 list 形式（多源场景） | 采用 dict 形式，与仓库主流一致 |
| 6 | 最初按 `--get-support` 写测试，本机演练即报 `Unknown option` | 脚本内部 okey 叫 `get_support`，CLI 选项名是 `--support` | 实测修正，并同步 MANIFEST/notes/README |
| 7 | **人工审查判 PR 不通过（rule4/rule8 少报）**：PR 把上游用例写成 0 | 首版只看了官方发布资产（确实不含测试目录），没查上游 git 仓库；实际上游有 `testing/` 回归套件 **2,589 例** | 如实更正数量，并**在真机上真实执行**该套件（2,354 例，PASS 1,667 / FAIL 686，70.8%），把失败按"缺可选模块 / harness 环境假设"归因后写进 MANIFEST/notes/PR |

## 源码修改

无补丁。上游脚本首行已经是 `#!/usr/bin/env perl`；鸿蒙 HongMeng Kernel 1.12.0 起
`/usr/bin/env` 存在（指向 toybox 的符号链接，见知识库 E037），真机已复核 `ls -l /usr/bin/env`。
`test_swaks.sh` 会先断言 `/usr/bin/env` 存在，再断言脚本首行，失败时给出 E037 的明确诊断。

## 验证结果

### 1. W0 依赖检查（含 perl 包内部模块清点）

R35 要求用 `conan download` 而不是 `conan list` 判断制品是否存在。本机与真机各做一次：

```bash
# 本机（全新 CONAN_HOME，避免本地缓存造成假阳性）
conan download "perl/5.42.2" -r=ohpcd
# → Downloading 17.0MB conan_package.tgz ... Download completed in 31s
#   package 6b129b068851896169fae42d399fa922d239ce8a
#   os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / libc++ / cppstd 17

# 真机（shadow CI 内）
bash ci/scripts/preflight_check.sh swaks/20240103.0
# → [OK] 已发布: perl/5.42.2
# → [OK] 版本号未被占用: swaks/20240103.0
# 真机 L0i: [ok] dependency in registry: perl/5.42.2
```

### 2. 配方与门禁（本机前置）

```bash
python -m py_compile conanfile.py test_package/conanfile.py      # 通过
python -c "import yaml; yaml.safe_load(open('conandata.yml'))"   # conandata/manifest/MANIFEST 均可解析
python -m json.tool archives/s/swaks/commands.json               # type=tool，含 20240103.0
conan export . && conan inspect .                                # 导出成功，元数据正确（隔离 CONAN_HOME）
```

CI L0 门禁本地仿真（按 `ci/conan/build_and_test.sh` 当前版本的 G0e + L0a-L0q 逐条复刻，**属仿真而非真 CI**）：
**16/16 通过**——test_package 结构（L0a-L0e）、patches 格式（L0f）、无硬编码 remote（L0g）、
`self.run` 无裸 shell 变量（L0h）、依赖 AST 解析（L0i）、软件级 `commands.json`（L0k）、
目录结构五条规则（L0m）、分支名（L0n）、无 curl/wget（L0o）、settings 四项（L0p）、
exports_sources（L0q）。

### 3. test_package 本机演练

用 Git for Windows 自带的 **perl 5.42.2**（与 OHOS perl 包同版本）驱动上游脚本：
`swaks consumer test: 27 passed, 0 failed`。反向验证（对齐 CI L1e/R34）：移除包内 `bin/swaks` 后
测试以 `FAIL: packaged CLI missing` 退出 1，说明测试确实依赖被测产物。

### 4. 真机 shadow CI（已通过）

设备：HarmonyOS / HongMeng Kernel 1.12.0 / aarch64。入口：`ohos-test-runner.sh` 隔离 job +
设备全局锁（本包运行时长约 16 秒，与其它会话的重任务排队共存，未绕锁）。

```
run_id : codex-swaks-20240103.0-swaks-20240103.0-r1-conan-20261015-150019-49419
command: zsh ci/conan/build_and_test.sh archives/s/swaks/20240103.0
exit   : 0
```

| 门禁 | 结果 | 证据 |
|------|------|------|
| G0e | pass | 根目录白名单通过 |
| L0 | pass | L0i `[ok] dependency in registry: perl/5.42.2`；L0j 版本未被占用；L0k `commands.json valid (type=tool)`；L0m 结构合法 |
| L1 | pass | `Launching test_package` / `Running test()` 出现在 `conan create` 日志；`SWAKS_CONSUMER_TEST_RESULT PASS=27 FAIL=0` |
| L1e | pass | `[sabotage] bin/ moved away` → `[ok] Negative test confirmed — test genuinely depends on swaks` |
| L2 | skip | `[warn] L2: swaks --version/--help failed (non-blocking)`（原因见问题 #3，非配方缺陷） |
| L4 | pass | 无补丁 |
| L5 | pass | `[ok] L5: bin/ has content` |

```
Build Summary
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
```

`conan create` 关键行：

```
swaks/20240103.0: Sources correctly downloaded from https://gh-proxy.com/https://github.com/jetmore/swaks/releases/download/v20240103.0/swaks-20240103.0.tar.gz
swaks/20240103.0: swaks 20240103.0: source script verified (244177 bytes, upstream shebang kept)
swaks/20240103.0: package(): Packaged 1 file: swaks ; Packaged 5 '.txt' files
swaks/20240103.0 (test package): RUN: PATH="<pkg>/bin:$PATH" "/system/bin/sh" test_swaks.sh ...
swaks consumer test: 27 passed, 0 failed
```

真机 27 条断言覆盖：`/usr/bin/env`（E037）、perl 运行时依赖确实进入 PATH、`Pod::Usage` 存在、
`--version`/`--help`/`--support`、socket 传输完整 ESMTP 事务（EHLO→MAIL FROM→RCPT TO→DATA→
结尾点→QUIT，逐行比对 sink 会话记录）、RCPT 被 550 拒绝时非 0 退出并回显原因、`--pipe` 管道传输。

### 5. test_package 之外的独立复核（真机）

手工模拟 `conanrun`（PATH 加依赖 perl/bin，PERL5LIB 指向依赖 perl5 目录），不复用测试脚本：

```
swaks --version   → "swaks version 20240103.0"                       rc=0
swaks --help      → 正常渲染 POD（NAME/DESCRIPTION）                  rc=0
swaks --support   → IPv4/v6 Socket Transport supported
                    Pipe Transport supported / UNIX Socket Transport supported
                    TLS not available: requires Net::SSLeay
perl -MPod::Usage / -MPod::Text / -MIO::Socket::IP / -MIPC::Open2 → OK
perl -MNet::SSLeay                                              → 无此模块（预期）
```

### 6. 上游回归套件实测（真机，应人工审查要求补做，第二轮已跑满）

上游套件不在发布资产里，而在 git tag 归档 `testing/`：**2,589 例 / 12 组**（`_options-data` 382、
`_options-output` 379、`_options-protocol` 374、`_options-tls` 252、`_options-auth` 246、
`_exec-transactions` 235、`_options-transport` 216、`_options-xclient` 166、`_options-proxy` 163、
`_options-processing` 113、`_exec-output-dump` 58、`_exec-output` 5），另有 7,718 个 `out-ref/` 期望文件。

#### 6.1 全量结果（2026-10-17，12 组全跑，无未执行组）

```
run_id : codex-swaks-20240103.0-swaks-upstream-full-20261017-111510-31879（453s，设备 runner 全局锁）
命令   : SWAKS_TEST_SWAKS=<pkg>/bin/swaks perl testing/regressions/bin/run-all.pl
结果   : Total 2589 / PASS 2133 / FAIL 455 / SKIP 1  → 通过率 82.39%
```

| 组 | total | pass | fail |
|---|---|---|---|
| _exec-output | 5 | 0 | 5 |
| _exec-output-dump | 58 | 48 | 10 |
| **_exec-transactions** | **235** | **122** | **113** |
| _options-auth | 246 | 240 | 6 |
| _options-data | 382 | 136 | 245（+1 skip） |
| _options-output | 379 | 364 | 15 |
| _options-processing | 113 | 67 | 46 |
| _options-protocol | 374 | 370 | 4 |
| _options-proxy | 163 | 163 | 0 |
| **_options-tls** | **252** | **252** | **0** |
| _options-transport | 216 | 205 | 11 |
| _options-xclient | 166 | 166 | 0 |

对照首轮（2026-10-15，`_exec-transactions` 因 `use Net::SSLeay` 无法执行）：2,354 例 / 1,667 pass /
686 fail（70.83%）；在**两轮都执行的 2,353 例**上，通过从 1,667 → 2,005（70.8% → 85.2%）。

#### 6.2 Net::SSLeay 阻塞已解除（真实现，不是桩）

设备 perl 的 `Config{cc}` 指向不存在的 `/data/service/hnp/bin/clang`，且 `perl Makefile.PL` 会
futex 死锁（`/proc` 显示 `hm_futex_wait_interruptible`、CPU 不增长），因此**绕过 MakeMaker 手工构建**：

```
xsubpp -typemap ExtUtils/typemap -typemap typemap SSLeay.xs > SSLeay.c
clang -fPIC -O2 -I$ARCH/CORE -I$OSSL/include -c SSLeay.c -o SSLeay.o
clang -shared -o SSLeay.so SSLeay.o -L$OSSL/lib -lssl -lcrypto      # 静态链 OHOS openssl/3.5.8.1
perl -MAutoSplit -e 'AutoSplit::autosplit(...)'                     # 手工构建必须补 AutoSplit
```

结果：`Net::SSLeay::SSLeay_version(0)` → `OpenSSL 3.5.8 25 Aug 2026`；`swaks --support` → `=== TLS supported`；
`_options-tls` **252/252 全过**；`_exec-transactions` **首次执行 235 例**（122 pass）。
同批还补了 CPAN 真实现：`Authen::NTLM` 1.09、`Authen::SASL` 2.2100、`Net::DNS` 1.57、
`Digest::HMAC` 1.05、`Net::IP` 1.26（NTLM/DIGEST-MD5/MX 认证随之可用）。

#### 6.3 剩余 455 例失败归因（重叠计数）

| 归因 | 例数 | 说明 |
|------|------|------|
| harness hostname munge 环境差异 | **418（92%）** | 设备 hostname 恰为 `localhost`，harness 的 `munge_local_hostname` 把它替换成 `LOCAL_HOST_NAME`，而上游 `out-ref` 里是字面 `localhost` —— 纯环境差异，改 swaks 无法消除。**含原误归为"perl 库路径"的 32 例 `062xx`**：用 `PERL5OPT` 修掉 `strict.pm` 报错后，露出真主因是 munge 连命令行里的 `--server localhost` 也替换成 `LOCAL_HOST_NAME` |
| 缺可选 Perl 模块 | **0** | `Socket6` 0.29 也手工编成**真实现**（手写 `config.h` + `xsubpp -noprototypes` + `clang -fPIC -shared`），配 CPAN 纯 Perl 的 `IO::Socket::INET6` 2.73；装好后 `swaks --support` **16 行全部 supported** |
| TLS/SSL 残留 | 4 | `Net::SSLeay`/SSL 相关少量残留 |
| 未归因 | 19 | unix-domain socket 3 例（`smtp-server.pl` 报 `Couldn't be a unix domain server`）、上游 ref 面向 git 开发副本（`DEVRELEASE`、`__END__` 布局）等 |

**披露**：① `Net::SSLeay`、`Socket6` 均为**真实现**（非桩），本轮**未新增任何桩**；② `Term::ReadKey` 仍是
编译期最小桩（headless 不调用，Net::SSLeay 之前就存在）；③ 所有补充都在 `$HOME` 环境目录，**未写入 swaks
conan 包、未改任何 conan 配方**，openssl 用独立 `CONAN_HOME`；④ **未修改任何上游 `.test` / `out-ref/` /
harness 代码，也未改 harness 的 munge 配置**；⑤ `PERL5OPT` 方案验证有效（strict.pm 32→0）但因
`_exec-transactions/05209` 回退 1 例、且 062xx 仍被 munge 判死而**回退未启用**。

#### 6.4 结论

上游套件已在 OHOS 上**全量跑通 82.39%（2,133/2,589）**：`_exec-transactions` 阻塞（Net::SSLeay）与
INET6 缺口都已用**真实现**解除，`swaks --support` 16/16 supported；剩余失败 **92% 是 harness 的
hostname munge 环境差异**（`hostname=localhost` 与上游 ref 的字面 `localhost` 撞车），其余为少量 TLS
残留与未归因，均非 swaks 配方缺陷。

### 7. 观察（非阻塞，供 PR 说明）

`ci-metadata.json` 的 `source_trace.url` 为空：CI 在扫描阶段把单值 `url:` 展开成 gh-proxy 镜像列表，
而 metadata 在还原官方 URL 之前生成，`awk` 取不到值（sha256 正常）。这是 CI 对 github.com 源的
通用行为，与本包 conandata.yml 写法无关。

## 注意事项

1. `perl/5.42.2` 在归档里是 `built`，但 ohpcd 上已有 OHOS 二进制包（真机 `conan create` 时成功下载
   17.0MB），本包依赖检查通过。若 perl 之后重新发布，需要重跑本包验证。
2. **L2 在本包上只能是 skip**：L2 不激活 conanrun，而 `perl` 不在设备 PATH 上（设备无系统 perl）。
   不要为了让 L2 变绿而把解释器路径硬编码进 shebang 或往包里塞 perl；PR 中按上述证据说明即可。
3. TLS（`--tls*`）在**包内**仍不可用（`perl/5.42.2` 制品不含 `Net::SSLeay`），`--support` 会如实报告。
   本次已在设备上手工编出 `Net::SSLeay` 1.96 验证「可解」，但那是测试环境侧准备；要让它成为
   **包的真实能力**，需要把 `Net::SSLeay`（及其 OpenSSL 依赖）做成独立 Conan 包并让 perl 可见，
   属依赖侧任务，不混进本 PR。
4. **上游用例口径**：上游套件 2,589 例（git 仓库 `testing/`，发布资产不含），本次真机**全量执行
   2,589 例、通过 2,133（82.39%）**；本包自身断言为 `test_package` 27/27。两者分开统计，不混写通过率。
5. 本机演练的临时 Perl 模块、L0 仿真脚本、dry-run 与真机证据都放在仓库外
   （`D:\harmonyos\scratch`），不进入交付物。
