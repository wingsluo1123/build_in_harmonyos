## PR 信息
- **三方库名称**：isc-dhcp（ISC DHCP——DHCPv4/v6 服务器、客户端、中继的经典实现，含 OMAPI 管理接口与 omshell 交互工具；4.4.3-P1 为 4.x 末代维护版本，与 ISC 新一代 Kea 属不同代际的独立实现）
- **上游版本**：4.4.3-P1
- **上游仓库地址**：https://ftp.isc.org/isc/dhcp/4.4.3-P1/dhcp-4.4.3-P1.tar.gz（sha256 `0ac416bb55997ca8632174fd10737fd61cdb8dba2752160a335775bc21dc73c7`，conandata.yml 钉死）
- **适配路径**：路径 B（知识库扩展），`archives/i/isc-dhcp/4.4.3-p1`（8 个补丁：7 个平台适配 + 1 个测试运行脚本适配；知识草稿 ×1 随本 MR 提交至 `knowledge/drafts/`，见「补充说明」）
- **使用知识库**：SKILL v12.22 适配流程；平台事实三条逐条命中——E011（HMDFS 用户卷拒收 mktemp 探测创建的 0700 目录，configure 无法建临时目录）、脚本直执行受限（内核拒绝直接 exec 非签名解释器脚本，`configure`/`install-sh` 均须 `$(SHELL)` 前缀调用）、R8（补丁全量为能力探测/工具链适配，无平台宏）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 13 程序 / 56 用例 | 来源：上游 `common/client/relay/server` 四组 `tests/` 目录的 13 个 ATF 程序（Autotools `make check` + atf-run 执行）：common 6 程序 25 用例（alloc/dns/domain_name/misc/ns_name/option）、client 1 程序 1 用例（duid）、relay 1 程序 3 用例、server 5 程序 27 用例（dhcpd/legacy/hash/load_bal/leaseq） |
| 集成测试 | 0 | 上游无 |
| 上游测试用例通过率 | 56/56（100%，0 失败 0 跳过） | 真机 `--with-atf` 接入后 `make check` 全量执行，四个 tests 目录 atf-run 退出码全 0 |
| **合计** | **13 程序 / 56 用例** | |

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例。8 个补丁中 7 个为平台适配（改点为顶层与 bind 子树的 `config.guess`/`config.sub`/`configure`/`bind/Makefile.in`），第 8 个（`0008`）为测试运行脚本适配：`tests/unittest.sh.in` 的 ATF 工具探测由 shell 特有的 `type | awk` 路径提取改为 POSIX `command -v`（OHOS 的 mksh 下 `type` 输出格式不同，提取结果错位致测试被静默跳过）——只改"怎么找到 atf-run"，不改变任何测试用例（程序/测试点/期望值），13 个 ATF 程序零增删零改动。
- [ ] **是**，存在对上游测试用例的修改（逐条说明）

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 13 程序 / 56 用例 | 不变 | 上游 13 个 ATF 程序原样保留并真机全量执行 |
| 集成测试 | 0 | — | 上游无 |
| 鸿蒙特有测试 | 7 校验点 | 新增 | test_package 消费者核验（4 程序实跑 + 3 API 校验点）：`dhcpd`/`dhclient`/`dhcrelay` 三件 `--version` 实跑（可执行文件 + 三库 + 捆绑 BIND 闭包在目标环境完成加载执行）、`omshell` 加载运行、链接三库的 OMAPI/dhcpctl API 消费者（`omapi_init`/`dhcpctl_initialize` 实调、`dhcpctl_connect` 连接路径实际执行） |
| 适配后测试用例通过率 | 56/56（100%）+ 7/7 | 持平 + 新增 | |
| **合计** | **13 程序 / 56 用例 + 7 校验点** | **+7** | |

---

## 上游测试用例修改说明

否：8 个补丁均不改变任何测试用例本体——7 个平台适配补丁的改点为 `config.guess`、`config.sub`、`configure`、`bind/Makefile.in` 四处；`0008` 只适配 `tests/unittest.sh.in` 中 atf-run 的定位方式（`command -v` 替代 `type | awk`），测试程序、测试点与期望值零改动。适配后另以 test_package 消费方视角补全鸿蒙平台验证（见上表鸿蒙特有测试行）。

## 验证结果

### 编译验证
- 编译器: clang 15.0.4（目标 aarch64-linux-ohos，musl libc）
- 构建系统: autotools（2014 年代树：顶层 configure + 子目录递归 Makefile，库为 plain `ar` 静态归档；内嵌 BIND 9.11.36 子树由 bind/Makefile 的 bind1/bind2 规则自解包、自配置、自构建，幂等可重入）
- 编译状态: 真机全量构建成功（dhcp 主体 + libdhcp/libomapi/libdhcpctl 三库 + 四个程序 + 捆绑 BIND 四库）；CI 侧 conan create（默认 `tests=False`，无外部依赖）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | 真机全量构建通过（构建与测试摘要见 reports/test-report.md） |
| 产物存在性 | ✅ | `bin/{dhcpd,dhclient,dhcrelay,omshell}` + 七静态库（libdhcp/libomapi/libdhcpctl + 捆绑 BIND 四库 isc/dns/isccfg/irs）+ 公共头（omapip 9 头 + dhcpctl.h + BIND 头全树）+ res 配置样例（上游安装产物逐项核验，另配方设 7 关键产物 fail-closed 检查） |
| 运行测试 | ✅ | 上游 13 程序 / 56 用例真机全量（0 失败 0 跳过，逐用例原始输出随档 reports/atf-run-*.out，摘要见 reports/test-report.md）+ test_package 7 校验点 |
| 许可证 | ✅ | `licenses/LICENSE`（MPL-2.0） |

### 补丁说明
8 个补丁（7 个平台适配 + 1 个测试运行脚本适配，逐条对照见 `notes.md`）：
1. `0001`/`0004-config.guess-harmonyos.patch`：顶层与 bind 子树两处 config.guess 加 HarmonyOS 探测分支（UNAME_SYSTEM=HarmonyOS 不在任何已知分支，configure 直接报无法识别构建主机类型），输出 `aarch64-unknown-linux-ohos`
2. `0002`/`0005-config.sub-linux-ohos.patch`：两处 config.sub 加 `*-linux-ohos` 模式（同期表无此模式，`--host=aarch64-unknown-linux-ohos` 校验失败）
3. `0003`/`0006-configure-E011-HMDFS-umask-fix.patch`：两处 configure 的 mktemp 临时目录探测对 umask 077 场景降为 022（HMDFS 用户卷拒收 0700 目录，探测必然失败）
4. `0007-bind-makefile-shell-prefix.patch`：bind/Makefile.in 中 bind 子树 configure 的调用由直接 exec 改为 `$(SHELL)` 前缀并显式 `< /dev/null`（脚本直执行受限，否则 `Permission denied`；该 configure 为 autoconf 产物，前导 `exec 7<&0` 需要可用 stdin，构建链中继承的 fd0 可处于关闭态时即报 `configure: line 577: 0: Bad file descriptor`，显式重定向保证 stdin 恒开）
5. `0008-tests-unittest-atfrun-command-v.patch`：tests/unittest.sh.in 的 ATF 工具探测改 POSIX `command -v`（mksh 的 `type` 输出格式致原有的 `awk '{print $3}'` 提取错位、测试静默跳过；bash/mksh/dash 输出一致）

配方内（无需补丁）的平台适配：`MKDIR_P` 归一（configure 后 walk 全树 Makefile，automake 回退出的 `.././install-sh -c -d` 改写为 `mkdir -p`——脚本直执行受限的配套处置）；BIND 头全树补装（上游 `make install` 不装 BIND 头，配方从 bind/include 源树补入）；etc 配置样例整体归置 res/isc-dhcp；捆绑 BIND 四库从 bind/lib 归一入包 lib/。

### 依赖
- requires(0)：无外部依赖。捆绑 BIND 9.11.36 四库（isc/dns/isccfg/irs）随包静态链接闭包交付；BIND 子树的加密/解析类可选依赖（openssl/libxml2/libjson/gssapi/lmdb）在 bind 内置 configure 选项中关闭，进程外无运行时依赖

### 测试结论
- 总体评价: 真机全量构建通过；上游 13 程序 / 56 用例 ATF 全量执行通过（0 失败 0 跳过）；conan-verify 八门禁结果见 reports/conan-verify-report.md；本地 CI 模拟（W3，平台同款 setup.sh + build_and_test.sh 流程）Success 1/1 全绿（结果摘要见 reports/test-report.md）
- 已知限制: `dhcpd`/`dhclient`/`dhcrelay` 为网络守护程序，真实流量验证需绑定接口、开套接字、维护租约库，包 CI 环境不可提供；验证口径=上游 ATF 套件覆盖服务器本体逻辑（协议状态机与配置解析）+ 消费者侧可执行文件加载与 OMAPI API 实际调用
- 上游测试用例通过率: 56/56（100%）
- 新增测试用例通过率: 7/7（100%）

### 遇到的问题与解决方案
1. **构建主机类型无法识别**（真机）：2014 年代 config.guess 不认 HarmonyOS（`UNAME_SYSTEM=HarmonyOS` 落入未知分支）→ patch 0001/0004 加探测分支输出 `aarch64-unknown-linux-ohos`，配套 patch 0002/0005 给 config.sub 加 `*-linux-ohos` 模式。
2. **E011：HMDFS 卷拒收 mktemp 探测目录**（真机）：configure 的临时目录自检以 umask 077 建目录，HMDFS 用户卷拒收 0700 → patch 0003/0006 把探测场景 umask 降为 022（只影响探测路径，不放松安装）。
3. **脚本直执行受限**（真机，多轮定位）：① 捆绑 BIND 子树的 configure 由 bind/Makefile 直接 exec 被内核拒绝（Permission denied）→ patch 0007 加 `$(SHELL)` 前缀；CI 链中同一调用另死于 `configure: line 577: 0: Bad file descriptor`（该 configure 为 autoconf 产物，前导 `exec 7<&0` 需要可用 stdin，而构建链中该调用继承的 fd0 可处于关闭态）→ 同一补丁给该调用显式 `< /dev/null`（stdin 恒开，对上游闭没闭均成立，三级复现 + 全量链验证通过）；② automake 生成的 Makefile 中 `MKDIR_P` 在 install-sh 模式下回退为脚本直 exec（创建 tests/.deps 等目录即败）→ 配方 configure 后把全树 Makefile 该行改写为 `mkdir -p`（`_fix_mkdir_p()`，幂等）。
4. **上游 make check 空转陷阱**：不接入 ATF 时 `make check` 只编译 `tests/libt_api.a` 即返回成功、不执行任何测试——若把这种"绿"当作测试通过即为假绿。另 OHOS 的 mksh 下 `type | awk` 提取 atf-run 路径错位同样导致静默跳过（patch 0008 修复）。本配方在 `tests=True` 而未提供 `user.isc-dhcp:atf_prefix` 时直接抛 `ConanInvalidConfiguration`（fail-closed），杜绝空转；真机执行外带 atf-0.19（环境侧工具，非交付物）完成全量。
5. **补丁链落点**：补丁 0004-0007 作用于捆绑 tarball 解出的 `bind/bind-9.11.36` 内层树，配方在应用补丁链前先解包内层 tarball（并利用 bind/Makefile 的 bind1/bind2 幂等规则，后续构建无需重复预铺）。
6. **Conan 打包两处修复**（CI 实证）：① `package_type="library"` 须声明 `shared` 选项，否则 Conan 2 在依赖图阶段直接拒载（`Package type is 'library', but no 'shared' option declared`）——修：声明 `shared`（默认 `False`，本包仅交付静态归档）+ `validate()` 拒绝 `shared=True`；② `package()` 原从硬编码 `staging/usr/local` 取件，而 `AutotoolsToolchain` 默认以 `--prefix=/` 配置（`--bindir/--sbindir=${prefix}/bin`、`--libdir=${prefix}/lib`），`make install` 实际落在 `staging/{bin,lib,include,etc}`，致包内漏拷三个 DHCP 库与四个程序（test_package 阶段 CMakeDeps 报 `Library 'dhcp' not found in package`）——修：`package()` 直接 `make install DESTDIR=<package_folder>`（仓库惯例，前缀 `/` 使安装直落 Conan 标准布局），并设 7 关键产物 fail-closed 检查。

### 验证命令
```
# 真机（HarmonyOS PC aarch64，conan 2.29.1，profile ohos-aarch64）
python3 scripts/ohc-run.py conan-verify isc-dhcp 4.4.3-p1
# 结果：见 reports/conan-verify-report.md

# 上游 ATF 全量（环境侧外带 atf-0.19）：
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -o tests=True \
  --build=missing --build="isc-dhcp/*" \
  -c user.isc-dhcp:atf_prefix=$HOME/atf19
# 结果：13 程序 / 56 用例全通过（0 失败 0 跳过）+ test_package 7 校验点全通过，RC=0（测试摘要见 reports/test-report.md；逐用例原始输出随档 reports/atf-run-*.out）

# 本地 CI 模拟（设备侧 bih 仓，平台 CI 同款流程：setup.sh + build_and_test.sh）：
zsh ci/conan/setup.sh
zsh ci/conan/build_and_test.sh archives/i/isc-dhcp/4.4.3-p1
# 结果：W3_SETUP_RC=0 + W3_RC=0，Success 1/1，Pass rate 100.0%（L0/L1/L2/L5 全 pass + L1e 破坏性负向测试确认真实依赖；L4 补丁危险函数扫描 warn 非阻塞）——原始日志因体积未随档（本地留存），结果摘要见 reports/test-report.md
```

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖（`common/client/relay/server` 四组 `tests/` 的 13 个 ATF 程序，真机 `--with-atf` 全量执行；另 test_package 7 校验点消费者核验见上表鸿蒙特有测试行）
- [ ] **是**，上游无测试用例，适配后补全了测试

## 补充说明
1. **守护进程形态**：本包交付的三个守护程序与 omshell 在 CI 中无法做真实网络流量验证（需绑定接口/开套接字/租约库），故以「上游 ATF 套件（服务器本体逻辑）+ 消费者侧加载与 API 实调」双层口径覆盖；`dhcpd_unittests` 等直接测协议状态机与配置解析，是最接近真实运行逻辑的可执行验证。
2. **捆绑 BIND 的交付形态**：BIND 9.11.36 仅取其四个库（isc/dns/isccfg/irs）作为静态链接闭包随包交付，不交付 BIND 工具本身；配置在 bind 内置 configure 中关闭全部可选外部依赖，保证消费者链接不引入额外 requires。
3. **与 Kea 系的关系**：本仓此前已有 kea/kea-hooks/kea-hook-* 等 3.x 系列（Meson 构建的新一代），isc-dhcp 为与之平行存在的 4.x 经典实现（autotools），两者不互相依赖、共存无冲突。
4. **路径 B 知识草稿（1 条）**：`knowledge/drafts/DRAFT-ohos-nonblocking-connect-refused-reports-nomore.kv`（同名 `.md` 成对）——OHOS 上「非阻塞 connect → 事件循环 → 独立等待层」架构中，连接被拒的错误码经事件循环/dispatch 层消费后以 NOMORE 上报的一类问题：语义识别口径、负向校验白名单 `{CONNREFUSED, NETUNREACH, NOMORE}`、禁止无限宽校验与尾点地址假通过。来源=本包 test_package 消费者真机实证（`reported: no more`）与包内 omshell 交叉复现（`dhcpctl_connect: no more`），结论与具体库无关，适用于同类架构的全部上游库与其测试判定。
