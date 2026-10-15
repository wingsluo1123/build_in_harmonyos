## PR 信息

- **三方库名称**：dbus
- **上游版本**：1.16.2；适配包版本1.16.2.1
- **上游仓库地址**：https://dbus.freedesktop.org/releases/dbus/dbus-1.16.2.tar.xz
- **适配路径**：路径 A（基础适配）+ 路径 B（知识贡献）
- **使用知识库**：E699及E2026101515251-draft-A139；settings语义、导出字节和真实RREV分别绑定

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 17 | 原注册且源码属于 test/internals/ 的独立组，不重复计入 TAP 子断言 |
| 集成测试 | 32 | 其余原注册组，含 name-test、bus、GLib、daemon 和 shell 入口 |
| 其他测试 | 0 | 当前原配置没有另行注册的入口 |
| **合计** | **49** | 原注册 ID 保留，r463同一事务执行全部49组，不缩分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 17 | 不变 | 原注册及断言保留 |
| 集成测试 | 36 | +4 | 原32组和正式安装包消费者4项 |
| 鸿蒙特有测试 | 1 | 新增 | 实际签名 daemon、EXTERNAL peer credentials、当前UID注册和查询，1/1通过 |
| **合计** | **54** | **+5** | 原49组为44完整、1部分、3账户条件错误、1整组跳过，不是54/54或49/49 |

45个Meson OK包含1个部分覆盖组，不能写成45个完整通过。六条内部权限跳过分别属于daemon fd-limit两叶和uid-permissions四叶，不是六个整组跳过。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改

1. 原只读`/tmp`监听入口改用真实UID自有私有socket根，保留注册、认证、错误和连接断言；intrusive测试构建不可安装。
2. fdpass依据真实传输容量分批发送，但仍发送总计255个描述符，保留完整payload、恶意sender断开、零投递及victim存活断言。
3. 原userdb仅在已有嵌入式测试条件下记录真实UID查询Error，然后执行原失败路径，不制造账户或降低断言。
4. 当前AI Review193358428指出的`__OHOS__`专属回收分支已移除。非Windows POSIX路径统一使用真实kill/waitpid及EINTR重试，保留原超时和退出状态检查；上游Windows GPid路径保留原GLib行为。0014补丁由官方自动生成并精确重放验证，不声称非POSIX进程句柄也可使用waitpid。

产品FD清理仍保留完整portable close/CLOEXEC，实际不可执行的close_range快路径及源码内联重定义共同受控。数字UID准入不伪造NSS，真实GROUP/console规则和认证仍失败闭锁。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

安装包API消费者4项及鸿蒙专项1项不能代替原49组。生产intrusive_tests=false；原上游在单独不可安装构建中启用intrusive/modular测试，GLib是实际测试依赖而非生产ABI依赖。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：44/49（能力限制；不宣称100%）
- 新增测试用例通过率：5/5（100%）

新事务`dbus-official-step35-1.16.2.1-20261015-r463`实际官方Finish step35及Conan build/package/test_package RC0，消费者4/4、鸿蒙1/1；原49组44完整、1部分、3账户条件ERROR、1whole SKIP及6内部权限分支完整保留。完整冻结链、唯一launch、own0/release/postrelease已独立核验。

- 被测基础HEAD：3006419400b88a4a103ac8a9e0ed4d42c98b5e8a；被测tree：5e7ffa9ac98bb89e4fc38f16dc1a9603d635d0c1。
- observer SHA256：86dbf07892f99da7448767a44f2e2ecd8e36843a9e7075b6f9be2b553ebaab6f。
- 正式日志SHA256：45f098f74b987731864df4c520a25e6c48a5354fb5de0e5b539d787ddfb318d7。
- 初轮r264正式CI实际RC0但冻结审计旧版本公式失败，独立保留，不追改或跨run拼接。

由于当前测试身份未具备原测试要求的具名账户/组、root或跨UID授权，以下分支前提未获满足。已按用户明确授权保留原分母及真实错误/跳过，不改系统账户、权限或认证，不写成通过：




本轮另修复平台build106917的真实资源失败：该Worker默认Meson compile -j20，Ninja报posix_spawn: Resource temporarily unavailable，尚未执行原测试。生产配方现通过Conan2.29.1支持的tools.build:jobs配置，把本配方Meson构建限制为1；保留原完整49组、源码、认证及消费者断言。新事务dbus-official-step35-1.16.2.1-20261015-r463的原生官方流程已完整通过，输入tree 5e7ffa9ac98bb89e4fc38f16dc1a9603d635d0c1、正式日志SHA256 45f098f74b987731864df4c520a25e6c48a5354fb5de0e5b539d787ddfb318d7、观察SHA256 86dbf07892f99da7448767a44f2e2ecd8e36843a9e7075b6f9be2b553ebaab6f，own0/release/postrelease已核验。旧106827为worker准备mkdir超时，旧106917仍保留FAIL。新HEAD的真实平台CI和Review须重新验收，尚不能称已提审或制品已发布。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e75463b084e66149852e44166b533486256d6e064e1a592c431159c11eec7388
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：4064f709e901c77a69d54dca3b5e1dd1d6a2db65f44b7be5eb8c142ca5da26d5
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：086a71c396c7cde67c211f3b6ba8cdbc025bd18c0957e5194a77ac44c574dc77
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：086a71c396c7cde67c211f3b6ba8cdbc025bd18c0957e5194a77ac44c574dc77
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7ceb2ba1cfb98e41b3646520043b16b245995336d19e8f398667ebca039de918
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7ceb2ba1cfb98e41b3646520043b16b245995336d19e8f398667ebca039de918
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7ceb2ba1cfb98e41b3646520043b16b245995336d19e8f398667ebca039de918
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7ceb2ba1cfb98e41b3646520043b16b245995336d19e8f398667ebca039de918
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d2bdb5b89b1eeffc2399da91807d25501fa9a1668abcd61662845163bcf4b144

本次还修复完整生产构建和原测试之后的安装重链接：平台request120356/build107219已实际执行原49组，但package()中的meson install又启动Ninja链接，并因posix_spawn资源不足失败。配方现使用Conan2.29.1支持的Meson.install(cli_args=["--no-rebuild"])，安装本轮已完成的生产构建；仍不分发intrusive测试构建，仍对最终安装ELF重新签名，原测试、身份/权限例外和消费者断言保持。新事务dbus-official-step35-1.16.2.1-20261015-r463已通过原生官方W3，输入tree 5e7ffa9ac98bb89e4fc38f16dc1a9603d635d0c1、日志SHA256 45f098f74b987731864df4c520a25e6c48a5354fb5de0e5b539d787ddfb318d7、观察SHA256 86dbf07892f99da7448767a44f2e2ecd8e36843a9e7075b6f9be2b553ebaab6f，本任务进程清零及释放/后释放已核验。旧平台失败保留，新提交的真实平台CI和Review仍须重新验收；此时不宣称已提审或发布。

## 补充说明

- **关联 Issue**：#3872
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：fix/dbus-1.16.2.1
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 官方上游仍1.16.2，适配包1.16.2.1；依赖修复任务15251已自行导入并领取，源分支fix/dbus-1.16.2.1，不重复旧任务。
- 本provider使用公开POSIX与既有跨平台抽象，不实现GUI widget/rendering，不借用下游菜单/色彩管理的GUI理由。当前HD1–HD4重判不支持高难认定，不把TAP点或重复分配循环膨胀为独立组。
- 新E草稿对记录settings声明格式单变量变更的实际RREV实验；保留历史失败。声明格式变更虽然保持四项settings的AST值，却会改变真实Conan recipe revision。D-Bus同名同版本双隔离export仅改变引号，实测RREV681974d62375e6f8db0f6400987cf1b3到0179452950dc09f62b8e12805aaf8139；旧版本或相同package_id不能代替新RREV/PREV的发布闭包。
- 本地正式成功及授权覆盖边界不替代新完整HEAD的平台CI/AI Review。不会自动合并、上传或把本地包宣称已发布；下游仍待正常发布。

原PR15092合并后的自动release118848/build105686上传拒绝os/arch元数据。本修复规范四项settings声明，语义值保持；引号格式对服务接收的因果关系仍待正式发布证实。只在合并且当前完整门禁通过后平台post-merge /release到ohpcd，并用实际Conan制品核验。
