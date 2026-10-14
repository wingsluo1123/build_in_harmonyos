【积分赛】feat(libmtd): 适配 libmtd 2.3.1-3（mtd-utils lib/ 四库）到 HarmonyOS PC

- **三方库名称**：libmtd（mtd-utils 源码树 lib/ 产出的 C 库集合：libmtd/libubi/libubigen/libscan + libmissing 兼容层）
- **上游版本**：2.3.1-3（Debian sid 包版本语义：上游 mtd-utils 2.3.1 + Debian 修订 3，源码即上游 2.3.1 官方 tarball）
- **上游仓库地址**：https://git.infradead.org/mtd-utils.git （发布源 https://infraroot.at/pub/mtd/mtd-utils-2.3.1.tar.bz2 ，sha256=03d9dc58ad10ea3549d9528f6b17a44d8944e18e96c0f31474f9f977078b83dc）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（config.guess/sub OHOS 识别补丁，patch-autotools-ohos.pl）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试（已实测执行） | 33 | 来源：tests/unittests（cmocka 框架，mtdlib_test 17 项 + ubilib_test 16 项，`-Wl,--wrap=open/ioctl/...` mock 设备访问）；cmocka 取自制品仓 cmocka/2.0.2，实测 33/33 全过 |
| 集成测试（未执行） | 37 | 上游 tests/ 全量资产 N=70（测试源文件 44 个 .c + 测试脚本 18 个 .sh + 7 个 Makemodule.am + unittests sysfs_mock 运行器 1 项），其中 37 项来自 tests/checkfs(3)、fs-tests(2)、jittertest(4)、mtd-tests(7)、ubi-tests(13)、ubifs_tools-tests(1) 的测试程序与脚本及支撑源——均需真实 MTD/UBI 内核设备（mtdram/nandsim 模拟）；OHOS PC 无 /dev/mtd* / /dev/ubi*（`ls /dev/mtd* /dev/ubi*` → No such file or directory，UFS/NVMe 启动），物理不可执行，逐项原因见 reports/test-report.md |
| 其他测试 | 0 | 无 |
| **合计** | **70** | 33 项已实测执行（全过）+ 37 项设备依赖未执行（附具体技术原因） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 33 | 不变 | 上游 cmocka 单测未修改、原样编译执行，33/33 PASSED |
| 集成测试 | 0 执行 / 37 声明 | 未变化 | 设备依赖，同上游不可运行（33+37=70 与上游资产数一致；见 reports/test-report.md 逐项原因） |
| 鸿蒙特有测试 | 14 | 新增 | test_package/test.c 消费者端到端用例：真实 API（libmtd_open/libubi_open 设备感知降级 + libubigen 几何派生与 EC 头生成断言），14/14 PASSED |
| **合计** | **47 执行 / 70+14 声明** | **+14** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为四个库的公开 API 新增 1 个消费者端到端用例（14 项断言），覆盖设备感知行为（无 /dev/mtd* / /dev/ubi* 时 libmtd_open()/libubi_open() 优雅返回 NULL）与可离线验证的纯函数功能（libubigen 图像几何派生、EC 头生成 magic/大端序）
> - **补全原因**：上游 6/7 测试目录需真实 MTD/UBI 内核设备，OHOS PC 无法运行；且上游测试面向 CLI 工具链，未覆盖「第三方消费者链接静态库」的使用形态
> - **新增测试文件清单**：
>   1. `archives/l/libmtd/2.3.1-3/test_package/test.c` — 消费者端到端用例（include 公开头 + 链接打包静态库 + 14 项运行期断言）

## 验证结果

- 编译状态：通过（conan create 干净构建 + conan-verify G0–G4/L2/L4/L5 全 PASS；本地 W3 模拟 PASS）
- 上游测试用例通过率：33/33 可执行项（100%）；全量资产口径 33/70（37 项需真实 MTD/UBI 内核设备，OHOS PC 无 /dev/mtd*，物理不可执行，逐项原因见 reports/test-report.md）
- 新增测试用例通过率：14/14（100%）

## 补充说明

1. **交付物形态**：mtd-utils 的 libmtd/libubi/libubigen/libscan 在上游全部是 `noinst_LIBRARIES` 静态库（.a），无 libtool 共享构建 → 配方按静态库打包（options.shared=True 显式拒绝），`package()` 手动安装 .a 与公共头（libmtd.h/libubi.h/libubigen.h/libscan.h + include/mtd/ UAPI 头）。消费者链接顺序 libmtd.a → libmissing.a 已在 cpp_info.libs 声明。
2. **零外部依赖**：四库仅链 libc；configure 以 `--without-tests --without-lsmtd --without-jffs --without-ubifs` 禁用全部 CLI 工具（这些才需要 libuuid/openssl/libselinux 等）。
3. **运行时语义**：OHOS PC 无 raw flash，库 API 如实返回 NULL（上游设计行为）；嵌入式 OHOS 板级有 raw flash 即可全功能使用。与 libv4l 类库不同，本包构建期零平台缺失。
4. **补丁**：2 个 portability 补丁（config.guess/config.sub 识别 HarmonyOS → aarch64-unknown-linux-ohos，知识库 E007 方案），已验证 git apply 干跑通过。
5. **ci/config/no_official_test.txt**：随本 PR 追加 libmtd 条目（asmjit/fabric/acpi_call 先例同做法），说明上游套件的设备依赖与单测实测证据。
6. **已知框架侧情况**：finish step8 SUMMARY.md 生成报 `'str' object has no attribute 'append'`（框架 bug，SUMMARY.md 属框架文件未在本 PR 修改）；submit 自检 packaging_present 为已知恒 FAIL 误报（要求 packaging/*.tar.gz，R19 禁手动打包），走手工等价路径，其余自检项与 Gate 0–3 均通过。
7. **版本号说明**：`2.3.1-3` 为任务指定的 Debian 修订号语义（源码同上游 2.3.1），ohpcd 制品仓无同名同版本记录（`conan download` 实证），无 R37/L0j 版本冲突。
8. **PF5/R8 平台宏例外披露**：patches/0001-config.guess.patch 第 7-8 行新增 `#elif defined(__OHOS__)` ——这是知识库 E007 方案（scripts/patch-autotools-ohos.pl）生成的 config.guess libc 探针，用于让 autoconf 在 HarmonyOS 宿主识别出 `aarch64-unknown-linux-ohos` 三元组（探针程序编译时按 libc 特征宏分类，属 R8 明文的「识别 libc 的探针程序」例外类）。不修 config.guess 则 configure 直接报 "cannot guess build type"，无 POSIX 兼容替代写法；config.sub 补丁无平台宏。
10. **补丁 0003（E011）**：configure 将 `umask 077` 改为 `umask 022`——HMDFS 的 UID 映射使 configure 以 0700 权限创建的 confXXXXXX 临时目录对构建进程不可写（CI 首轮报 `./confXXXX/subs1.awk: Permission denied / config.status: error: could not setup config files machinery`）。umask 022 在 CI 单用户构建场景下安全，知识库 E011 标准方案。
9. **与 PR #13835（libubi 2.3.1-3）的关系**：两者同源于 mtd-utils 2.3.1 lib/，属并行下达的两项独立适配任务，包目录/分支/conan 包名互不相同（libmtd vs libubi），JC6 单包原子性无冲突。形态差异：本 PR（libmtd）走 autotools 正规构建、按上游 noinst_LIBRARIES 分库存放 5 个 .a（libmtd/libubi/libubigen/libscan/libmissing），并完整交付 libmtd.h/libscan.h/libubigen.h 公共头与 33 项上游 cmocka 单测实测；#13835 将 6 个 noinst 库合并为单一自包含 libubi.a。消费方可按需选择分库版（本包）或合并版（#13835）。
