- **三方库名称**：shfs（SSH filesystem，Miroslav Spousta）
- **上游版本**：0.35
- **上游仓库地址**：https://shfs.sourceforge.net/ （官方主页；源码官方直链 https://sourceforge.net/projects/shfs/files/shfs/shfs-0.35/shfs-0.35.tar.gz/download ）
- **适配路径**：路径 B（贡献创新）——3 条新的可复用错误模式已写入知识图谱草稿
- **使用知识库**：openharmony-compile-agent（SKILL v12.x）。复用条目：E483（无扩展名下载 URL → BadZipFile）、E276（源码格式嗅探）、E2010（OHOS 无 `/etc/mtab` 时 mountlist 回退）、`DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary`（`mount(2)` 被 seccomp 拦截的消费者测试构造）、`DRAFT-ohos-syscall-capability-matrix-fork-probe`。本次新增草稿：`E2141`（clang 拒绝 GCC 遗留 `-I-`）、`E2142`（OHOS libc 缺 `addmntent(3)`）、`E2143`（tar 符号链接成员 → conan source→build 复制 EACCES）。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：`shfsmount/shell-test.in`、`shfsmount/perl-test.in` —— 上游唯一自带的测试工件，是随 mount 工具发布、被投递给远端 shell/perl 执行并把结论读回的能力探测脚本 |
| 集成测试 | 0 | 上游无测试目标：顶层 `Makefile` 的 target 只有 `all/clean/install/uninstall/utils*/module*/docs*/dist/distclean/deb*/rpm*`，`make -n check` 报 `No rule to make target 'check'` |
| 其他测试 | 0 | `docs/`、`rpm/`、`debian/` 内无测试代码 |
| **合计** | **2** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | U1/U2 逐字执行上游两个探测脚本（脚本随包分发到 `res/shfs/`，从打包产物侧调用，不依赖源码树） |
| 集成测试 | 5 | +5 | C1–C5：对打包后的 `bin/shfsmount`/`bin/shfsumount` 做 CLI 契约端到端验证（版本串烧录、usage、未知协议在建连接前失败、非法挂载点分支、卸载三入口） |
| 鸿蒙特有测试 | 2 | 新增 | 针对鸿蒙平台特性的测试：H1 以本机 `/bin/sh` 顶替远端主机跑通 shfs 协议全链路，并断言进程恰好停在 `mount(2)` 被 seccomp 拦下的 SIGSYS(159)、`/proc/mounts` 无残留；H2 非 root 应用 uid 下的挂载选项装配 + root-only 选项门禁 |
| **合计** | **9** | **+7** | 用例数 == 断言数 == 9，与 `test_package/MANIFEST.yml`（`assertion_count: 9`）、`reports/test-report.md` 三处口径一致 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

`shell-test.in` 与 `perl-test.in` 原样随包分发并原样执行。3 个补丁全部作用于构建输入，不涉及任何测试文件：
`0001` 改 `shfsmount/Makefile` 的 include 开关；`0002`/`0003` 改 `shfsmount.c`/`shfsumount.c` 的 mtab 写入实现。
唯一与"上游测试如何被运行"相关的取舍是：shell 协议的**全链路**（`shell-code.in` 的 `s_init`）没有做成自动化用例，
脚本本身未改，详见「补充说明」第 3 条。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无正式测试框架，适配后补全了测试

- **补全的测试范围**：上游只有 2 个能力探测脚本，没有任何 `check` 目标，也没有断言框架（脚本只回 `ok stable`/`ok stable preserve`，由 `shfsmount` 自己读结论）。本次补全 7 条：2 条鸿蒙特有端到端用例（H1/H2）+ 5 条 CLI 契约用例（C1–C5），覆盖协议握手全链路、挂载选项装配、非 root 门禁、版本戳、usage、未知协议分支、非法挂载点分支、卸载三入口。
- **补全原因**：上游把"测试"实现为运行时的远端能力探测（探测结果决定走 perl 还是 shell 协议），没有离线可执行的单元测试；且本平台的核心差异面（`mount(2)` 被 seccomp 拦截、以非 root 应用 uid 运行、musl 无 `addmntent`）在上游那 2 个探测脚本里完全体现不出来，必须新增平台特性用例。
- **新增测试文件清单**：
  1. `archives/s/shfs/0.35/test_package/test_shfs.sh` — 9 个用例，断言按用例级 pass/fail 计（用例内部合计约 30 个检查点，任一失败即该用例记 FAIL）；末尾用 `CASES -ne 9` 自检锁死用例数，防止用例漂移后统计口径失真
  2. `archives/s/shfs/0.35/test_package/conanfile.py` — `VirtualRunEnv` 下调用上述脚本，把被测包的 `package_folder` 作为唯一入参（消费者视角，不引用源码树）
  3. `archives/s/shfs/0.35/test_package/MANIFEST.yml` — 上游 2 项测试的来源/命令逐条登记 + `assertion_count: 9`

## 验证结果

- 编译状态：通过（`conan create` G1–G4 + W3 本地 CI 全绿，`reports/conan-verify-report.md` 为工具产物并附两处勘误；产物为 ELF 64-bit aarch64 `OHOS` / musl）
- 归档 `status` 记 `built` 而非 `published`：配方本身验证通过但尚未 `conan upload` 到制品仓，按 SKILL 状态值口径 `published = verify 通过 + CI upload`，上传由合并后的发布流水线完成
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：7/7（100%）
- 套件总通过率：9/9（100%），`9 cases run, 0 failed`

## 补充说明

1. **只构建用户态部分**：shfs 0.35 是「Linux 内核模块 + 用户态 mount 工具」混合体，顶层 `all: module utils docs` 的 `module` 分支进 `shfs/` 编内核模块。本平台无内核模块加载能力，配方只 `make -C shfsmount`，交付 `shfsmount`/`shfsumount` 两个命令（`package_type="application"`，R38 已配 `archives/s/shfs/commands.json`）。
2. **`mount(2)` 边界不是缺陷**：鸿蒙 seccomp 拦截 `mount(2)`，`shfsmount` 走完全部用户态流程后恰好停在 SIGSYS(159)。H1 把这个停止点 + `/proc/mounts` 无残留固化成断言，而不是"绕过它"。因此 `addmntent` 替换（补丁 0002/0003）只有链接期证明——运行期走不到 `update_mtab()`；这点在 `reports/test-report.md` 里单独成节说明，未计作通过项。
3. **shell 协议全链路只做手工验证**：上游 `shell-code.in` 的 `s_init` 对硬编码路径 `/tmp/._shfs_.<i>` 逐个 `mkdir` 试探，失败时用 `expr` 自增重试到 10000 次。本机 `/tmp` 可写时首试即中（全链路 ~1s），不可写时退化为 10000 次 fork——最坏分支下限实测 4 分 15 秒（计时对象是裸自增循环，不是整条挂载链路）。本机的 `/tmp` 是 hmfs 上的 `drwxrws--- 1076:expert` 实体目录而非 tmpfs，可写与否只取决于运行 uid 是否在 `expert` 组，所以该分支会让用例耗时随沙箱成员身份漂移，因此 shell 侧只自动化上游探测（U1），全链路端到端走无循环的 perl 分支（H1）。手工记录：`shfsmount -t shell -c "exec /bin/sh" -vvv -n <mnt>` → `Testing shell... ok stable` / `selected: shell` / 两次 `reply: ### 200` / SIGSYS(159)，形态与 H1 一致。
4. **许可证判定**：上游 `COPYING` 为 GPL-2.0 单文本，但 `debian/copyright` 写 "version 2, or any later version" → 配方按 `GPL-2.0-or-later` 记，`COPYING` 原文随包进 `licenses/`。
5. **无 conan 依赖**：`shfsmount/Makefile` 的 `LOADLIBES` 为空，两个二进制只链 OHOS sysroot 的 musl libc，`requirements()` 为空；`GnuToolchain` 只导出编译环境变量。R33 落实：编译器取自 `tools.build:compiler_executables`，不裸用 shell 的 `${CC}`。
6. **三条新知识的可迁移性**（这也是选路径 B 的理由）：`-I-`/`-iquote` 命中所有 2000 年前后手写 Makefile 的老项目；`addmntent` 缺失命中所有自写 `/etc/mtab` 的挂载助手（sshfs/fuse-utils/smbnetfs/mhddfs/curlftpfs/zfs 用户态）；tar 符号链接成员 → source→build 复制 EACCES 命中所有归档内含软链的配方（Debian `debian/changelog`、`docs/` 软链、autotools `config.guess` 软链），且这条给出了"失败早于 `build()`，在 `build()` 里删链接删不到"这个反直觉判据。
7. **需人工确认适配完整性**（R40：挂载助手属"系统底层"类，编译通过 ≠ 适配完成）：
   - 已端到端证实的能力面 —— shfs 协议握手（perl 分支全链路）、挂载选项装配、非 root 门禁、两个命令的 CLI 契约（`test-report.md` 的 9 项）。
   - 未证实/受平台能力限制的部分 —— 真正的挂载动作本身（`mount(2)` 被 seccomp 拦为 SIGSYS，见补充说明第 2 条）与 mtab 写入分支（只有链接期证明，运行期到不了）。
   - 结论口径：若使用场景需要**真实挂载点**，本包在鸿蒙 PC 上不具备该能力，须由平台侧挂载接口或特权环境承接，请勿按"已可用的挂载工具"验收；若需要的是协议侧工具与脚本生态（远端能力探测、选项装配、卸载器契约），本包完整可用。这一取舍不由适配者单方判定，故在此显式标注待人工确认。
