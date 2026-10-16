## PR 信息

- **三方库名称**：perl-net-daemon（Net::Daemon）
- **上游版本**：0.52（包版本0.52，上游模块身份保持）
- **上游仓库地址**：https://metacpan.org/release/TODDR/Net-Daemon-0.52
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2026101515306-draft-A139，解释器旧模式策略与当前并发后端实际覆盖分别验收。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 18 | 官方t/*.t原程序；原TAP另计93个断言，不把客户端循环累加为新用例 |
| 集成测试 | 0 | socket/fork/ithreads均包含在上述原程序中，不重复计数 |
| 其他测试 | 0 | 无另外的注册入口 |
| **合计** | **18** | 同版本原源码SHA256及全部18个程序ID保留 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 18 | 不变 | 16完整通过、2部分通过；93 TAP中90PASS/3SKIP、0失败，无整程序跳过 |
| 集成测试 | 0 | 不变 | 原forkm/ithreadm各10客户端×1000轮均实际运行，不重复统计循环 |
| 鸿蒙特有测试 | 1 | 新增 | 真实HarmonyOS、实际非root UID/无具名NSS、同UID原Bind及真实TCP socket生命周期 |
| **合计** | **19** | **+1** | 新增消费者3项另计，原3个受限断言不计通过 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

18个原t/*.t逐文件SHA256与官方tarball一致，原make test TEST_VERBOSE=1完整执行；所有原计划、TAP身份、数学/协议/错误检测断言及原fixture保持。三个原SKIP及Sys::Syslog的真实Unix socket警告原样保留。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

安装包消费者3项：Options真实参数解析；Clone独立对象和原post-hook行为；真实文件日志写入与读回。它们直接加载已安装的Net/Daemon.pm、Log.pm和Test.pm，不能替代原18个程序。

鸿蒙特有测试1项：原生uname确认为HarmonyOS，当前实际UID20020084且无getpwuid名字，原Net::Daemon::Bind在真实本地TCP监听socket上执行同UID生命周期并核对UID未变。没有授予root权限，不把同UID运行等同于永久降权。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：16/18（能力限制；不宣称100%）
- 新增测试用例通过率：4/4（100%）

原mode.t的2个SKIP分别由Perl<5.10、MSWin32条件限制；本次实际Perl5.42.2/HarmonyOS不适用。当前fork与ithreads原并发socket测试已完整执行。原privdrop.t第3断言只限Linux root，本次实际非root；其非法UID变化必须报Fatal的原断言真正通过。16完整、2部分不改称18/18或100%。

- 能力例外：t/mode.t/legacy-perl；结果：SKIP；原因：ABI_NOT_APPLICABLE；证据：6e5e00f406f2ca57a355e8fe084166b605959f3fc54ec091e190515220cb993e
- 能力例外：t/mode.t/windows-socket-duplication；结果：SKIP；原因：ABI_NOT_APPLICABLE；证据：df8375414652fae484461d621870fa6f00bf97df1218a5bcbba123ff4c8bef71
- 能力例外：t/privdrop.t/saved-set-user-id-root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：bb420938e56a0f64d52fdd86676b39084dbb9f43221218e3346db6a8fd355f05

两次独立正式create分别完整执行，不跨run累加。正式ConanVerifier/Finish35 RC0，消费者3及Harmony1，15回执30WAL、唯一launch、own0/release/postrelease已独立核验。原W3日志SHA256 d3152970b2c39309d4251d0c2b30106eeea607437d0f8a6bd67b84460fe482aa；观察SHA256 2baaf7757b4e766c0ca62645db2405e73bcc40c7ca3579851f091f02ab13194a。配方只使用真实已发布Perl5.42.2及其Core模块，私有安装布局不改变Perl ABI。平台CI、AI Review、提审及发布仍须分别回读。

---

## 补充说明

- 关联 Issue：#4064
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/perl-net-daemon-0.52
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：依赖任务15306，用于PlRPC → DBI原RPC模式 → wallet。旧正式r312因未分类原SKIP失败、r319因私有CI配置CRLF校验失败均保留；r328是全新事务，不追认旧运行。当前尚无正式制品发布证明，只有合并后平台正式发布并实际隔离下载成功后才用于父项W0。
