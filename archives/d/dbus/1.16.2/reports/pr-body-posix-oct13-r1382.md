## PR 信息

- **三方库名称**：dbus
- **上游版本**：1.16.2
- **上游仓库地址**：https://dbus.freedesktop.org/releases/dbus/dbus-1.16.2.tar.xz
- **适配路径**：路径 A（基础适配）+ 路径 B（知识贡献）
- **使用知识库**：E2026100904-draft-DBS2.kv/md；公开 POSIX 回退、真实进程域探测与子进程回收边界

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 17 | 原注册且源码属于 test/internals/ 的独立组，不重复计入 TAP 子断言 |
| 集成测试 | 32 | 其余原注册组，含 name-test、bus、GLib、daemon 和 shell 入口 |
| 其他测试 | 0 | 当前原配置没有另行注册的入口 |
| **合计** | **49** | 原注册 ID 保留，r1371同一事务执行全部49组，不缩分母 |

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

同一新鲜事务`dbus-official-step35-1.16.2-20261013-r1371`实际官方Finish step35及Conan build/package/test_package RC0，消费者4/4、鸿蒙1/1，原49组结果完整保留；唯一launch、完整链、own0、release/postrelease独立核验。

- 被测基础HEAD：21f197fca9ec6ff8e8707b1b982aee07a1a3fddb；修复tree：dab3aaededafedbc412a39a200bccc9377f091b2。
- observer SHA256：00e9fdeee79aca736237a1a8d6136130b45d8f8d26c866cdd77d27b57235b775。
- 正式日志SHA256：e33695c4258bcc8e8b0054f7a170375a9d82a9ad33ebf7a15454b732e5a5db3a。
- 原材料manifest SHA256：b33572508900c3156fe7ed646984751fc956fbe4d92d7b56c88632df767fc200。
- 旧r1317真实RC1、ForkFailed及执行错误完整保留，不追改为通过，不跨run拼接。

由于当前测试身份未具备原测试要求的具名账户/组、root或跨UID授权，以下分支前提未获满足。已按用户明确授权保留原分母及真实错误/跳过，不改系统账户、权限或认证，不写成通过：

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：cdbdaf43386b452acf556caf9a1cae0e7a448dbc5618f142f62647d73cfa846a
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c17b3fbfa933571e9a07b36174abe7062cf34a50eb08b4ce3e6a89a1454885be
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：2012a7117b25a3bd9a1062406af263edda3839c582c42a44e4fdca1c40698c8f
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：2012a7117b25a3bd9a1062406af263edda3839c582c42a44e4fdca1c40698c8f
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e166bbedf5100a14b481c3bd44127739a00ad61fa03f85416101b5aa78f15749
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e166bbedf5100a14b481c3bd44127739a00ad61fa03f85416101b5aa78f15749
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e166bbedf5100a14b481c3bd44127739a00ad61fa03f85416101b5aa78f15749
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e166bbedf5100a14b481c3bd44127739a00ad61fa03f85416101b5aa78f15749
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：071a316a4592360ef6238ab521d33e7fc6d7430a5d9d1268347ab6a7311c9e61

## 补充说明

- **关联 Issue**：#3872
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：2301_80739235:feat/dbus-1.16.2
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 官方源码、1.16.2版本与既有任务身份不变，不重复旧1.14版本或他人任务。
- 本provider使用公开POSIX与既有跨平台抽象，不实现GUI widget/rendering，不借用下游菜单/色彩管理的GUI理由。当前HD1–HD4重判不支持高难认定，不把TAP点或重复分配循环膨胀为独立组。
- E草稿对包含源码内联syscall及通知/子进程实际回收的可复用边界；保留历史失败，内部流程规则不夹带。
- 本地正式成功及授权覆盖边界不替代新完整HEAD的平台CI/AI Review。不会自动合并、上传或把本地包宣称已发布；下游仍待正常发布。
