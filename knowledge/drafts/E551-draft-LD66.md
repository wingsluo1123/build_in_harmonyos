# E551 — 验证权限夹具的内核前提，而不只检查 chmod 返回值

## 场景和根因

负向 IO 测试先 chmod(directory, 0)，随后期望异步创建/写入报告 EACCES。
若缓存位于 HMDFS，chmod 返回成功不等于内核实际拒绝当前用户的写入。
若环境包装器又把 TMPDIR 指向缓存，则原生可写临时目录的权限语义也会丢失。
这与代码签名 Permission denied、SELinux 拒绝或 worker 无法 fork 不同。

真实案例：libdispatch 6.4.1 PR15756，CI92608（CI-011）完成编译，36/37
测试通过，dispatch_io 的权限回调实际0、预期EACCES=13。不是下载或依赖失败。

## 可复用修复

1. 不信任环境变量的名称。worker 原始 TMPDIR 也可能在 HMDFS；保存变量
   不等于保留 DAC 能力。依次检查该根和应用沙箱的 temp/cache 根，不写死用户目录。
   每个候选只创建唯一 mkdtemp 夹具；chmod(000) 后独占 open 必须精确 EACCES，
   恢复0700后同一路径必须成功创建，清理该私有夹具后才选择根。没有合格根即失败。
2. 仅把依赖 DAC 的夹具移入该根下的唯一 mkdtemp 目录，其他测试布局不变。
3. chmod(0) 后，直接 open(O_CREAT|O_EXCL|O_RDWR) 验证精确 EACCES。
   若意外成功，关闭并删除探测文件，随后明确失败；其他 errno 也不能接受。
4. 保留原异步错误、全部未写入数据和后续成功写入/读回断言。同步探测不替代
   异步测试，也不另计一个测试用例。
5. 重新执行完整注册清单和安装包消费者。不同链接模式分别计数，不拼分母。

## 验证与边界

此前验证记录在 `archives/l/libdispatch/6.4.1/reports/permission-fixture-ci-repair.md`。
此前原生 Conan r8 shared/static 各37/37及消费者1/1通过；两份JUnit
同时保存同步EACCES13、异步EACCES13及未写入数据256的精确PASS输出。
正式日志SHA256为3b537ce0c62a034c466d6d34d99d027705ee6ca645f5a8206f969d7221599ea5。
未完成的收尾或平台CI不提前宣称通过，旧 CI 和旧真机 PASS 不证明新输入。

CI93083（CI-021）在原始 TMPDIR 上再次出现内核探测 Actual0/Expected13，
证明旧的“保存 TMPDIR 即可”假设不足；不是已解决后的 worker fork 故障。
新增能力选择只处理夹具前提，不把配方探测计作新上游测试；最终证据以本轮报告为准。

候选能力选择的新验证为Conan r12：在210132上串行shared/static各37/37及
消费者1/1通过，两份JUnit均记录同步EACCES13、异步EACCES13及未写入256。
日志SHA256为7b6fb4238a0b7837a97c29a78df3f8f868afb230c6da45fc704f67b8742e3cb1。
完整边界和后续收尾见 reports/worker-dac-ci-repair.md；不把旧r10/r11的失败
事务或旧finish r8拼接为这次PASS，也不据此宣称比赛worker已经通过。

若全部候选根都不执行 DAC，或者用户持有 DAC 覆盖权限，本方案必须失败，
不能改成接受成功、无条件 skip、退化成其他 errno 或声称权限保护已验证。
只操作任务私有目录，不修改系统挂载、用户权限或其他任务文件。

## 与既有知识的增量

E046 已记录“chmod 不生效”，但推荐 skip；本任务要求全量无跳过，不能套用。
E223 验证私有临时数据的正向 owner/mode/MAC/读写闭环，而非拒绝写入的
异步错误传播。本条不重复申报已知根因，增加夹具能力前提、环境变量覆盖边界、
唯一私有目录和同步/异步双层精确 errno 验证，适用于其他 IO/文件权限套件。
它不替代 HMDFS 签名执行许可知识，也不等同于 E550 的大小写命名空间隔离。
