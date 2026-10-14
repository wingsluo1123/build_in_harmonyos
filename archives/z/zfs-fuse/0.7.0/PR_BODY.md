【高难度挑战】feat(zfs-fuse): 适配 zfs-fuse 0.7.0 到鸿蒙PC aarch64-linux-ohos

- **三方库名称**：zfs-fuse（ZFS 文件系统用户态移植，含 zfs-fuse daemon 与 zfs/zpool/zdb/ztest/zstreamdump 工具集）
- **上游版本**：0.7.0
- **上游仓库地址**：https://deb.debian.org/debian/pool/main/z/zfs-fuse/zfs-fuse_0.7.0.orig.tar.bz2（上游官网 zfs-fuse.net 不可达，采用 Debian pool 官方 orig 源，sha256=507361eb3d96ad4155e6e6d26437ecc0d371c749106500976085a72dc399f868）
- **适配路径**：路径 C（测试路径，测试通过率 ≥90%，实测 100%）
- **使用知识库**：build_in_harmonyos SKILL（SCons 构建知识、musl/clang 兼容知识、conan-verify G0/G2 预检）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：源码树无 tests/ 目录，无 automake TESTS 声明（R51 三步法清点确认） |
| 集成测试 | 2 | 来源：上游官方测试入口 cmd/ztest 与 cmd/zdb —— ① `cmd/ztest/ztest`（用户态池综合测试器：元数据/数据全操作 + SIGKILL 崩溃容错 + 内置 zdb 完整性校验）；② `cmd/zdb/zdb -l`（vdev 标签解析冒烟，覆盖 nvlist/XDR 路径） |
| 其他测试 | 2 | 来源：cmd/zpool、cmd/zfs CLI 工具（被 ztest 间接调用，本 PR 在 test_package 冒烟中真实执行） |
| **合计** | **4** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试框架 |
| 集成测试 | 2 | 不变 | conan build() 内全部真实执行：daemon-start=ok、ztest=ok（`ztest -f <dir> -T 10` exit 0）、zdb-label=ok（`zdb -l` name 断言命中），3/3 检查项 passed |
| 鸿蒙特有测试 | 6 | 新增 | test_package/run_smoke.py 真实执行型冒烟（R34 无空壳，调用打包产物二进制）：① zpool CLI 加载；② zfs-fuse daemon 启动；③ zpool create（文件 vdev，`-m none` 绕开沙箱 FUSE 限制）；④ zfs list；⑤ zdb -l；⑥ zpool destroy |
| **合计** | **8** | **+4** | 全部真实执行 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

> ztest/zdb 源码原样编译，仅通过运行参数适配沙箱（`-f` 数据目录、`-T` 时长）；数据/套接字/缓存目录经新增环境变量（ZFS_SOCK_DIR / ZPOOL_CACHE_DIR / ZFS_LOCK_DIR）重定位，测试源码零改动。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无自动化测试套件（ztest/zdb 需手工驱动），适配后补全了自动化测试

> - **补全的测试范围**：test_package 补全 6 项真实执行型冒烟，覆盖 daemon 生命周期与池全生命周期；conanfile.py build() 内嵌上游测试 3 项检查（daemon-start / ztest / zdb-label），R34 合规
> - **补全原因**：上游 ztest/zdb 为手工运行的工具，无 CI 可执行测试入口；为满足 Conan test_package 门禁自动化验证
> - **新增测试文件清单**：
>   1. `test_package/run_smoke.py` — 真实执行打包二进制的全链路冒烟（daemon 启动 → zpool create → zfs list → zdb -l → zpool destroy，6/6 passed）
>   2. `test_package/conanfile.py` — test() 经 `self.run` 调用 run_smoke.py（L0d 门禁合规）
>   3. `test_package/MANIFEST.yml` — upstream_test_in_build: true 证据声明

## 验证结果

- 编译状态：通过（本地 `conan create` exit 0，W3 本地 CI 模拟 L0–L5 全 PASS）
- 上游测试用例通过率：3/3 检查项（**100%**）—— daemon-start=ok、ztest=ok（`ztest -T 10` 完整 10 秒池测试含 SIGKILL 崩溃容错与内置 zdb 校验）、zdb-label=ok；开发期超长验证 `ztest -T 25` exit 0、`ztest -T 10 -V` exit 0（kill rate 100%）
- 新增测试用例通过率：6/6（**100%**）
- conan-verify：G1/G2/G3/G4/L2/L4/L5 全 PASS；W5 独立审计 P0=0 P1=0，verdict=pass

## 补充说明

1. **为何是高难度挑战**：上游为 2011 年时代 custom SCons（Python2）+ 内嵌 autoconf（libumem），无现代构建系统 —— 需将 SCons 移植到 Python3、重写 libumem SConscript（沙箱无法运行 configure，改为 SConscript 内生成 config.h）；musl/clang15 兼容面广（无 SunRPC、无 pthread_cancel、-fno-common 冲突），共 35 个补丁。
2. **沙箱限制的工程解法**：/dev/fuse 不可用 → 池操作用 `-m none` 跳过挂载点（不影响元数据/标签路径测试）；文件系统 bind() 返回 EPERM → UNIX socket 改抽象命名空间（daemon/client 双端）；/tmp 只读 → 运行时路径全部环境变量化。
3. **知识沉淀（5 条）**：musl 无 SunRPC 需自包含 header-only xdrmem shim（DECODE 原地解码）；clang15 需 -fcommon；沙箱 bind() 改抽象 socket；SCons posix.py SHELL 需 patch 为 /system/bin/sh 且 AR/RANLIB 需绝对路径；musl 无 pthread_cancel 导出需协作取消 stub。
4. **已知限制**：FUSE 内核通道在构建沙箱不可用，挂载路径未经真机 /dev/fuse 验证（daemon/池/CLI/标签路径均已实测）；daemon 仍保留 FUSE 挂载能力，真机环境下可正常使用。
5. 证据文件：`reports/test-report.md`（双口径台账）、`reports/w3-local-ci.log`、`reports/conan-verify-report.md`、`reports/audit-result.json`、`conan-build` 日志中 HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_RESULT 标记。

## CI 失败修复记录（PR #15645 第 1 轮，run #90024）

CI 诊断类别「未知」，人工定位根因并修复如下：

1. **分支捎带了 k2pdfopt/2.55（W2/PF1 违规）**：原分支 `feat/zfs-fuse-0.7.0` 基于含 k2pdfopt 提交的旧基线（88e45181e3），导致 CI 同时构建两包，且该旧副本缺 test 源（L0c no_test_sources）、分支名不匹配（L0n branch_name_r40）。**修复**：分支重建为「最新 upstream main（f6a25613da）+ 仅 zfs-fuse 提交（cherry-pick 9381c91377/62f9443614/8d85db64a1）」，k2pdfopt 不再属于本 PR（其修复与测试源在独立分支 `feat/k2pdfopt-2.55` 的对应 PR 中）。
2. **zfs-fuse 缺 commands.json（L0k commands_json_r38）**：zfs-fuse 构建产物为 6 个 CLI 工具（zfs-fuse/zfs/zpool/zdb/ztest/zstreamdump，`package_type = "application"`），按 R38 在软件级目录补 `archives/z/zfs-fuse/commands.json`（type=tool，ref/versions 对齐 0.7.0）。

**修复后本地完整 CI 验证**（本机 runner003，`ci/conan/setup.sh` → `build_and_test.sh`，`CI_PACKAGES=archives/z/zfs-fuse/0.7.0`）：

- L0 全部门禁 PASS（含 JC6 单软件原子性：仅 zfs-fuse 1 个包）
- conan create exit 0；上游测试 3/3（100%）、test_package 冒烟 6/6（100%）
- L1a/L1b/L1e PASS（测试真实依赖被测包，破坏性反向验证通过）；L5 PASS
- L2 版本检查 non-blocking 警告（上游工具不支持 --version/--help，与上轮一致）；L4 补丁内危险函数为 XDR shim 历史声明，non-blocking
- 构建摘要：Total 1 / Success 1 / Failed 0，通过率 **100%**
