## PR 信息

当前验证以 `dbus-official-step35-1.16.2-20261011-r008` 为准：完整输入 HEAD
`f51bc9899f17ceab7cd40924eee2d4a5930e9950`，tested candidate tree
`faefed552fca7c3708464e4db737beab69eac463`。本轮修复原自有子进程回收超时：
保留 SIGTERM、原测试断言与 300 秒超时，仅在目标域对精确 spawn 子 PID 执行
真实 waitpid，检查 EINTR、PID 和终态。新事务不再出现 TIMEOUT，原 daemon
组实际完成。官方 step35/Conan create RC0、消费者4/4、鸿蒙专项1/1。
原49组完整执行，仍为44 CLEAN、1 PARTIAL、3 ERROR、1 whole SKIP，内部6条
权限 SKIP；这是45个 Meson OK，不是49/49通过。

由于当前受控应用账户未具备原测试所需的具名账户、tty组、root与跨UID权限，
相关验证暂不具备完整执行条件。保留实际错误、跳过、原分母及逐项证据，供
具备相应授权的环境补充验证；不模拟账户或弱化认证。新软件超时已单独修复，
不纳入这些能力限制。当前逐项证据如下：

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：ca695a83f0fdd4febf5cf03d239753f76899ffb18495120ac0196fd46b3a9b2f
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：400dc4165addce03531d9677f5866b7dcac67ed1132ae60f5dce3bf32be0bf01
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：73664d2b13cf9efa2d625d7272b17871ce80f58e84c081cd8d436802709155b0
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：73664d2b13cf9efa2d625d7272b17871ce80f58e84c081cd8d436802709155b0
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：587eea03fce6945cc22c6a055576f2e62f66f34b60c092f73f5a58322a67f054
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：587eea03fce6945cc22c6a055576f2e62f66f34b60c092f73f5a58322a67f054
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：587eea03fce6945cc22c6a055576f2e62f66f34b60c092f73f5a58322a67f054
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：587eea03fce6945cc22c6a055576f2e62f66f34b60c092f73f5a58322a67f054
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：61d1d4b04121100ba0df2910f052cde312ec8f7271095865fd82bdb0e498356b

独立完整事务 observer SHA256
`20d62345acf90637b84cd8cbe82409882c018b4991eeb1c725e82ec30599711f`；
原自动 step35 marker SHA256
`659282bf8aac2a854757a9810a9ac9af1f97661a7fdf74c63d9fd129daaaf364`；
原 W3 日志 SHA256
`56b980b5b36435a4e7312cbfbefd048d4c5135e5157c1cedc7203ac23ad43f1a`；
Conan 日志 SHA256
`9ea6cd0b59c78bd4866fe0a07ccd8d0f3715b2641f74d552e6f15ff0b561c96b`。
唯一 launch1、完整 WAL/receipt、own0、release/postrelease 已独立核验。
以下 r006 及更早段落是保留历史，不替代当前结果，不跨事务汇总，不证明平台CI或发布。

当前候选的实际验证为 2026-10-11 `dbus-official-step35-1.16.2-20261011-r006`，tested tree `3d87e2ec505f922a3b424cdc62c35b8923e1b524`。本次修复 CI 的私有临时目录所有权失败：未显式配置时优先选择实际 UID 所有、无符号链接且可写的目录；显式错误配置仍失败闭锁，不改账户、系统权限或上游断言。原官方 step35/Conan create RC0，49/49 原组均执行，结果为44 CLEAN、1 PARTIAL、3 ERROR、1 whole SKIP，六条断言 SKIP；消费者4/4、鸿蒙专项1/1，不能称49/49通过。

独立完整事务核验 SHA256 `d9946c4a456a6623dbbb594307d442e7a28da87ff90793a921c0a2f48d3c8a3c`；原上游日志 SHA256 `13c86d0fed3a370fba0712f26d5a62ff147e56d9a18b601f004e9a5df305d887`；Conan 日志 SHA256 `990bd6ae50271dae397f5737d4af3d2103f009807f1c09c03e72fc563179fa89`；原自动 step35 回执 SHA256 `7f72fcc81c8cc0fd9200beb4c0175d98e58163aee1ae1b46ad69abd35a5bf37f`，其日志 SHA256 `fa4c033b39d29f0432ea0f040177ab41b716e64105805b3822a31ce235210b82`。唯一 launch1、完整 WAL/receipt chain、own0、release/postrelease 已核验。本地正式验证不是平台 CI、提审或发布证明。

由于当前受控目标账户不具备原用例要求的具名 tty 组、当前 UID 的 passwd 条目及 root/跨 UID 权限，下列具体路径仍保留原 ERROR/SKIP，并按已授权能力披露规则进入评审和 CI；未模拟账户或弱化认证。以下仅为本次同一 r006 的逐项证据，不与历史合并：

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a4e36fca009074518d727b8d1c7d93a3958542541da4e11f4b045acbdb3d1590
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：88caab93f4feb61eec1e278e76103874d3a2fd8fce6942a22abd967072cc35db
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：2aae757284a40209b709c629515045a1acea6d14e162c020383164b118dd7fd1
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：2aae757284a40209b709c629515045a1acea6d14e162c020383164b118dd7fd1
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d6fff81ef4c363113d73dcce5cf7ee1d7de3b06f269814c2ab7004c022e96764
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d6fff81ef4c363113d73dcce5cf7ee1d7de3b06f269814c2ab7004c022e96764
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d6fff81ef4c363113d73dcce5cf7ee1d7de3b06f269814c2ab7004c022e96764
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d6fff81ef4c363113d73dcce5cf7ee1d7de3b06f269814c2ab7004c022e96764
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：ac811acd623e7aeab21b329b4a30c2c4c724004672beb4bee7eb3d8be77be734

以下 2026-10-09/10 的 r004/r005/r006/r008/r013 段全部为保留历史，不作为本次运行态、正式回执或跨 run 汇总。当前结果以以上 2026-10-11 r006 为准。
本次仅为平台 build93870 的原上游入口断言补充具体失败阶段、实际 RC 和原始日志尾部，保留全部原布尔条件、原49个注册组和能力接受规则。原平台失败的确切根因仍待新 HEAD 的实际日志核对，不能由本地成功追认平台通过。
同一新事务 `dbus-stable-formal-1.16.2-20261010-r013` 实际正式 Conan create RC0、原49组44 CLEAN/1 PARTIAL/3 ERROR/1 whole SKIP，消费者4/4、鸿蒙专项1/1；不宣称49/49。独立 observer SHA256 `26421846082accb8a569c46b82757718a97837ddb27f1e6b29ad0f18713fd42a`，原上游日志 SHA256 `41434d2f32d8b5ca78310dd4c3e3af72119540fe1951200f53359cb40016cdcc`，Conan 日志 SHA256 `73b68eb242b8a3261f88fbd8882963926cc8cc099359598bbc86816a16730052`。唯一 launch1、完整 WAL/receipt chain、own0、release/postrelease 已独立核验。
本次修复真实平台 CI #79470 的 Meson 归档器查找失败：OHOS 没有显式 ar 时，由配置的实际 Clang 查询工具路径，验证可执行文件与 `--version` 后向 Meson 传入绝对路径；显式错误 ar 不偷偷回退。普通 Linux 未配置 ar 时保留 Meson 默认行为。
同一新事务 `dbus-official-step35-1.16.2-20261010-r008` 正式 Conan/step35 RC0，实际 49 原组为44 CLEAN、1 PARTIAL、3 ERROR、1 whole SKIP，消费者4/4、鸿蒙专项1/1，原 fdpass15/15零跳过。独立完整回执链 observer SHA256 `b4a751f9c4b4d6b85b22ead3cf5c8bd1962c89cc8b126b7707d9d91fac337723`。实际 recipe SHA256 `fead9fc548509dbfc1c983fe4c32978c2c1c12d43bcc52cde167eb98bc7af186`，tested candidate `ead9fdfb9be67be6bf6689335710035d3649a7c2`。全部真实 ERROR/SKIP 与原49分母保留；不是49/49、制品发布、平台CI或提审PASS。
平台旧 HEAD `ef87780eabc60a1215a297771323f60b26ed87d7` 的 request104817/build91451 已实际失败于 `llvm-ar --version FileNotFound`；本次本地修复通过不追认旧CI为通过。当前候选提交后须等待对应完整HEAD的新平台Review/CI。

- **三方库名称**：dbus
- **上游版本**：1.16.2
- **上游仓库地址**：https://dbus.freedesktop.org/releases/dbus/dbus-1.16.2.tar.xz
- **适配路径**：路径 A（基础适配）+ 路径 B（知识贡献），唯一标题前缀【知识库扩展】。HD1–HD4 均 false，当前重判 dbus-hd-reassessment-oct09-r003.json SHA256 e587d14da3e6a49d932e52c3b0dded90fbc27f8aeac18e0d695fd65a58ea4c76。普通 D-Bus 异步派发、测试加载器及账户缺失不是特殊调度修复。
- **使用知识库**：knowledge/drafts/E2026100904-draft-DBS2.kv 与同 stem .md（draft: true）。新增结论为 libc 负向探测后源码 raw-syscall 重定义的能力边界，保留原完整描述符安全语义；本次真实 bool/Error 因果定位和 Conan 原破坏负例补充已沉淀至全局知识。

真实终态为 dbus-official-step35-1.16.2-20261009-r004：HEAD b95978a4750e7aa9a3d49af148bb3bbedf81051d，staged tree 047de2ff37540797ffa211eefa3701ca60e24f53，endpoint 10.62.201.39:2222、boot cecf80c5-0d8c-4003-b8e1-24adacc80dfd、UID20020084。官方原 FinishPipeline.step35_local_ci、生产 package 与 test_package 同 run 执行。正文/状态元数据更新不改已测生产源码、配方、补丁或测试输入，但提交前仍须重新绑定 candidate tree。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 17 | 实际注册且 srcs 含 test/internals/ 的独立组；不重复计入 TAP 子断言 |
| 集成测试 | 32 | 其余实际注册组，含 name-test、bus、GLib API/daemon 及 shell 入口；为互斥登记分组，不声称上游自行作此分类 |
| 其他测试 | 0 | 当前配置没有另一组额外注册入口 |
| **合计** | **49** | r004 同一 run 完整执行，不缩分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 17 | 不变 | 保留原 internals 注册组、原 ERROR 与断言 |
| 集成测试 | 36 | +4 | 原其余32组及同 r004正式消费者4/4；原49合计45 OK、3 ERROR、1 whole SKIP，daemon仍含权限SKIP |
| 鸿蒙特有测试 | 1 | +1 | 同 r004 实际签名 daemon、EXTERNAL peer credentials、实际 UID 注册和查询；1/1 PASS、零 skip |
| **合计** | **54** | **新增5** | 混合登记单位，不是 54/54 或 49/49 PASS |

组级语义为 44 CLEAN、1 PARTIAL、3 ERROR、1 SKIP。六个内部 TAP SKIP 是 uid-permissions 四叶与 daemon fd-limit 两叶，不是六个 whole SKIP。原 upstream-summary 的 passed=false、failed_groups、whole_skipped_groups、实际 RC 与原日志均保留。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例。
- [x] **是**，存在对上游测试用例的修改。

1. 原只读 /tmp 监听失败的 test/corrupt.c、loopback.c、relay.c、internals/refs.c、internals/server-oom.c 与 tmp-session-like-system.conf.in 改用任务私有 socket 根；原注册 ID、错误断言、安全语义不变。
2. test/fdpass.c 按真实 OHOS 传输容量分批发送，仍发送总计 255 个描述符；完整 payload、恶意 sender 断开、零投递及两个 victim 连接存活断言不变。

产品 dbus-sysdeps-unix.c 只避开真实 SIGSYS 的 close_range 快路径，保留完整 portable close/CLOEXEC。policy/userdb 在无 GROUP/console 规则的数字 UID 准入中延迟不必要 NSS 查询，真实组规则、命名账户与认证仍 fail closed。此次 userdb 仅在原 DBUS_ENABLE_EMBEDDED_TESTS 宏下、实际 UID lookup false 点保存 Error 类型和文本，再执行原 error_free/return false/640 fatal warning；生产 intrusive=false 无新日志。未删或放宽原 49 项断言。

11 个源码补丁均由官方 refresh-patch 入口生成。新 0004 的官方 dry-run、真实 patch_ng 字节重放、其他十补丁不变与最小旧共享文案拒绝/typed NSS 接受结果 SHA256 dc44678aaa911bb64ff4cf9baee9cb81ef60756c4a47fb908def73efbcdb77dc；r004 正式 Conan 已从真实原归档重放并构建。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖。
- [ ] **是**，上游无测试用例，适配后补全了测试。

新增 consumer.c 四项 API 检查与 harmony_tests/numeric_external.py 一个鸿蒙专项，只增加消费者及运行时覆盖，不替代原 49 组。HARMONY_TESTS.yml 绑定真实 Conan 入口；1/1 marker 在全部原断言成功后输出。MANIFEST.yml 的旧未执行状态是提交前静态声明，实际本轮执行以 r004 原日志/回执为准，未为更新状态修改已冻结 CI 输入。

正式生产 intrusive_tests=false；原上游在另一个 intrusive=true、不可安装的 build 执行，不安装不安全测试库或 daemon。GLib 为实际 host test_requires，不伪造为生产 ABI 依赖；expat 公开依赖保留。数字 UID 专项只允许总线驱动必需 receive 规则，保留 EXTERNAL、实际 UID 与原断言。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：44/49（能力限制；不宣称100%）
- 新增测试用例通过率：5/5（100%）

r004 官方 FinishPipeline.step35_local_ci 实际 RC0，生产 build/package 和正式 test_package 成功。原49为44 CLEAN、1 PARTIAL、3 ERROR、1 whole SKIP，六个内部权限SKIP；45个Meson OK不等于45个完整PASS。新增5项为消费者4/4与鸿蒙专项1/1，同run分别统计、零skip。这不是全上游或 Pre-PR PASS。

原方法自动 .ci-result.json SHA256 af1af7d023bd3f61aa00f6556b3b3fd4f80b8b8d427eab057ab24128d0205841，step=W3_local_ci、exit_code=0；其 log_sha256 与实际 w3-local-ci.log 的 40ed19dccf90ffb80cc00e0ccee59b24b06607a49f645b6f9acf7678f8da2e88 相符。原 Conan log SHA256 37aabe4708fa0871e5cee815d9a3df9cb6b39f40517df2708a5ae05cb1d8bd69。唯一 launch1、原 WAL/receipt chain、release/postrelease、own0 已完整核验。Observer SHA256 5a2c850be6e76e512d5b7c5cfd625606ad2ae7369ae7b41d50ced22eb046fe19；原材料 manifest SHA256 81d286932563f42a8acaa96844666ec4bd0d680a61ae86d231cf0556880d2c65。

官方 L2 为五个 CLI smoke 成功、五个非阻塞失败，不声明 10/10。原 L1e 单次负例实际使用 host/default build profile 同 SHA256 03d14bb8cbee1bd1014c654f440737741c525ce7dc55dbbc2579b60e8effc1cc；原 lib/ moved away 后进入 test_package/CMake，明确 Library 'dbus-1' not found in package、RC1。原负例 stderr SHA256 afff9ac28be0a3275085d36e37b5dbd9566a89b6f7ebd9bb570642fa5897a330；独立只读因果补充 SHA256 2f31dcb5f2a43bc4692f0ccd794d38ed8eb10740ab1951ade687fab2f245774c。没有新增负例调用、修改官方判定或追改历史结果。

本轮本地 Conan 身份为 dbus/1.16.2#667074f990dfaf21bc7869d151777c05:e27c6e11a9aaaffa60a19ae18d800cf8ce5fb247#bcee86d350a0c46ea63bb45133cd1295。该私有包已按原合同清理；不是制品仓发布身份。

## 补充说明

按用户要求公开保留此次已实际证明的目标账户/权限缺口：

- dbus - dbus:bus，RC -6：原 test/data/valid-config-files-system/many-rules.conf:21/41/50 的 tty 具名组规则，实际 Unknown group "tty"；未伪造组或改为数字策略。
- dbus - dbus:misc-internals，RC -6：原 auth-script:640 当前用户名 false。本次实际 Error 为 DBUS_USERNAME_UID_LOOKUP_FAILED uid=20020084 error=org.freedesktop.DBus.Error.Failed message=Looking up user ID 20020084: not found，随后原 no memory for username fatal warning。已直接区分 NSS 与分配/锁/字符串等未知失败；共享警告本身不作能力证明。
- dbus - dbus:userdb，RC -5：原 /userdb/groups_from_uid、test/internals/userdb.c:77–78 的当前实际 UID20020084 lookup not found。具名 root UID0 存在，不声称全局 NSS 不存在，不把 root 条目当本进程有 root 权限。
- runs-dbus-daemon - dbus:uid-permissions，whole SKIP：/uid-permissions/uae/other、/uid-permissions/monitor/root、/uid-permissions/monitor/messagebus、/uid-permissions/monitor/other 四叶实际 cannot use alternative uid when not uid 0。原 getuid root gate、getpwnam、真实 setuid 与 UID/EUID 校验不改。
- runs-dbus-daemon+slow - dbus:dbus-daemon 的 OK 行仍含 /fd-limit/session 与 /fd-limit/system 两叶实际 root 权限 SKIP；原提高 fd limit 和替代 UID 要求不改。

全部原 case/branch、真实 stdout/stderr SHA、RC、来源行和来源文件 SHA 保存在 dbus-capability-source-ledger-oct09-r004.json，SHA256 0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a。独立 misc-r002 只用于先前精确定位，不与 r004 拼分母。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：0d3fbba9c466367a3537f94ea586f53a3f0d9ca08b63daef3c2e55ada60db60a

显式 user.dbus:task_capability_acceptance=closure-oct08-nss-permissions-v1 默认关闭，只在真实 OHOS 非 UID0、自身 passwd/tty 组缺失、原 49 名称/RC/typed ERROR 与六叶完整原因精确匹配时允许继续 package/test_package。旧共享警告、NoMemory、其他系统错误、额外 FAIL/SKIP、未知原因和临时 OOM 一律 fail closed；不伪造 NSS/auth/primaryGID，不改系统账户、权限或服务。原 passed=false 保留；不是全上游 PASS、canonical Pre-PR PASS 或提审豁免。

- 关联 Issue：#3872 https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3872；PR：#15092；PR 链接：https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/15092；当前状态：open。
- 队伍名称：天天开心。
- 申请人显示标识：2301_80739235。
- 源分支：feat/dbus-1.16.2
- 目标分支：main
- 平台任务14988实际assigned/已领取、活动开源鸿蒙PC专项积分赛-依赖，readback SHA256 06e1c82d31e29690712d233a7aaa0d7230b360106780099927bd01c41c9b9618。
- 正式 dbus/1.16.2 发布尚未证明。最后 exact --build=never 查询（2026-10-08）result.json SHA256 94fe562896e9f0a79918d33d1808298901b4415b492e7e5464f9fdc3e4d7d669 为 recipe not found，无远端 RREV/PID/PREV；menu/colord 的 R36 仍独立阻塞，不以本地包或能力接受代替发布。
- 当前 E2026100904 同 stem KV/MD、draft:true 由官方 graph.py 真实验证 1KV/1MD/1index、RC0、零 warnings，dbus-own-pair-schema-oct09-r005/result.json SHA256 1dcfd59991d49c7cfe2b07da52c2bb170615ebf7e422d244bff4e2b96161534f。与 r004 旧 E699 对相比仅知识身份/路径变化，知识正文语义不变，原目标不重测。这仅为本对 schema，不是完整 W5。主线 a5bda0fd270676a04e3e63d48b83f51c75e62666 四scope 7104/7104 内容逐SHA绑定：dbus-main-knowledge-contents-oct09-r001/manifest.json SHA256 cfdb5d129b7c48d5e9b29ce5ebb61ad92a78f48ccb846f214b52cc4b6c5b2ea8；E699 在另一任务正文实际占用，本对迁移 E2026100904 的路径/正文0、完整OPEN2526身份记录0，原raw-syscall匹配0。最终提交仍须根fresh main API身份相等及合同绑定。
- 新 PRE_CREATE/POST_CREATE、最新当前 HEAD 平台 Review/CI、真实提审与后续 release 仍须根逐项完成。旧事务不重放、不跨 run 拼 PASS，不上传或合并。Valgrind 工具的实际 SIGSEGV 属于未修软件问题，不归类为本次可接受账户限制。

### 当前评审整改与独立验证（2026-10-09）

AI192794651已实际修复：Meson close_range feature 默认auto，只有明确disabled生成DBUS_DISABLE_CLOSE_RANGE，生产及原intrusive构建同选项，原全部close/CLOEXEC回退保留。官方refresh-patch --auto生成并精确重放三文件差异。新事务r005实际原step35/Conan create RC0，49原组44clean、1含跳过、3ERROR、1整组SKIP；消费者4/4、鸿蒙1/1。observer SHA256 0a1f07d57a2b880d80d90f94e039a7e1c46c17a252544c60847ccc4d1d62bc5c，原日志SHA256 49ade2e476e96e6832c25a7d6ee78a699fcb15a9fac620e4a750aa37309a8983。原具名账户/组/root/跨UID限制保留，不算全量PASS、正式发布或提审豁免。

以下为当前r005逐原case日志绑定；前述r004为历史，不跨run合并。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d01b3d653595eacf490a2551aa45b4b50f5b71a6aec68acd5ab9e22a38a355ab
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c608eb261445538efebf094d74c0bbbe97ea079ec56854afca43948f32378a99
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a00fdfa4592780a24e7003581cfdb7a4f290b03b38493f673c40694e0be4797b
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a00fdfa4592780a24e7003581cfdb7a4f290b03b38493f673c40694e0be4797b
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：3c8ae68a95967fdd614adaf7ce753387e2a0d94693d3642993f50b264dd756f8
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：3c8ae68a95967fdd614adaf7ce753387e2a0d94693d3642993f50b264dd756f8
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：3c8ae68a95967fdd614adaf7ce753387e2a0d94693d3642993f50b264dd756f8
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：3c8ae68a95967fdd614adaf7ce753387e2a0d94693d3642993f50b264dd756f8
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：5a4407c4c532a7664383a1a0af510f63084a8ed3e70dab8624196129ba608c06
### 当前 fdpass 评审整改与独立验证（2026-10-10）

AI192963572 指出的测试平台宏已实际移除：所有平台共用原32-fd分批循环，
保留累计255描述符、完整载荷、sender断连、被拒消息零投递及无辜连接断言。
正式生成补丁并精确源码重放，不改变产品FD上限或认证策略。
同一新事务 dbus-official-step35-1.16.2-20261010-r006 原fdpass15/15零跳过，
官方step35/Conan create RC0、消费者4/4、鸿蒙1/1。
独立observer SHA256：1828a52578f1f214342f125e9562e4dfa42a981bb32f1c181a10962bae9520bb。
原日志 SHA256：1122b514776d29ea37af9658917244c49016b470d989e52ad144e3305a3e4a52。
原49组为44 clean、1部分跳过、3 ERROR、1整组SKIP；具名账户、组、root和
跨UID的实际能力缺口仍未通过，不宣称全上游PASS、发布或提审，只申请已授权
能力披露范围内的重新检视及当前候选CI。

### 当前 r006 的逐项能力证据

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：9b24fcc9fe8b592a5cbd782fca3fc5311dfd6fc94c2e1e2da2bd7f652ed95509
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：abfa564883a73e6b51d9f044091e5e244036af965bbc39f8a556621eb666f26e
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：604de5d891bb18aedef8bab4d202d37aa04e195c1d595ff86701347beec586bf
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：604de5d891bb18aedef8bab4d202d37aa04e195c1d595ff86701347beec586bf
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a2ef6195ee0bc710c9333279d439ed0f686ad45bc615fd43310070dc960593bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a2ef6195ee0bc710c9333279d439ed0f686ad45bc615fd43310070dc960593bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a2ef6195ee0bc710c9333279d439ed0f686ad45bc615fd43310070dc960593bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a2ef6195ee0bc710c9333279d439ed0f686ad45bc615fd43310070dc960593bc
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：1a5910acca195f587c8c61ed509ec37f12f9f05ac98ecc2e4aa50c14ad651ce1


### 当前 r008 的逐项能力证据

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e5c5bad10c513e1df060373939379092b6b1154d661d7f2f2367d113c68b312f
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：744b50464dafa6742da7e99bbb25932feca55b32849ad0ee2b3f25c43442a069
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e0c0cc0262bcb9b75ad1d61ef6f9729843c1f68ef18f11512e4dcb86e1a58f8c
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e0c0cc0262bcb9b75ad1d61ef6f9729843c1f68ef18f11512e4dcb86e1a58f8c
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c5f5a9e66aa6545fa8934b8da0fe94b89f033882ef81227bb3632d0ac6da0094
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c5f5a9e66aa6545fa8934b8da0fe94b89f033882ef81227bb3632d0ac6da0094
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c5f5a9e66aa6545fa8934b8da0fe94b89f033882ef81227bb3632d0ac6da0094
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：c5f5a9e66aa6545fa8934b8da0fe94b89f033882ef81227bb3632d0ac6da0094
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：3a3805788b65298049e928cfcee1e2166d7d311f699ee6d30bf0415583e21f69

### 当前 r013 的逐项能力证据

由于当前应用测试账户未具备原测试所需的具名账户/tty组、root及跨UID执行条件，相关账户查询、权限切换与描述符限制验证暂不具备完整执行条件。我们保留其原组与分支、实际 ERROR/SKIP 和诊断证据，供具备相应受控条件的环境补充验证；不模拟账户、不绕过认证，也不将这些结果计为通过。其余真实软件故障仍单独阻塞，不纳入此能力说明。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a83e03e27cf9f4c1ac2aa6a8733e3d77c2210f531888bb5dfe608b7843d9bcc4
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：d0b15a3e080f71a9f4ac53a1069ca9619d2d4818d42594166d7d277178cadd53
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：21016b288d18a7163195aa93b17bcf70d9d04d19508d2f368b85f40c24a2fcc0
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：21016b288d18a7163195aa93b17bcf70d9d04d19508d2f368b85f40c24a2fcc0
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a3ec70226c2e74a43b3ea00536b6c4e5ef7d1079f16e1be5f16d7ee484de92bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a3ec70226c2e74a43b3ea00536b6c4e5ef7d1079f16e1be5f16d7ee484de92bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a3ec70226c2e74a43b3ea00536b6c4e5ef7d1079f16e1be5f16d7ee484de92bc
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：a3ec70226c2e74a43b3ea00536b6c4e5ef7d1079f16e1be5f16d7ee484de92bc
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：dedea86e5661c6a1790db2900781fb8f8ea2bdfd312165f0f7ceb8bec241f3eb

### 2026-10-11 r011：完整私有 intrusive 构建修复（历史）

修复平台 build97367 实际 XDG_RUNTIME_DIR UID 归属失败：独立 intrusive
测试构建整体移入经过真实 UID/无链接/可写核验的任务私有根，并保留签名器
WORK 边界。生产包仍从原 intrusive_tests=false 的生产构建安装；原49注册、
认证、布尔断言和超时不改。原 Meson 日志逐字节导出并绑定来源。

同一新事务官方 step35/Conan create RC0，原49组全部执行：44 clean、1部分
跳过、3 ERROR、1整组 SKIP；消费者4/4、鸿蒙1/1。独立 observed SHA256：
`6d565883efaf04ea5efe26542dd0297beb1360d972690208aacdae1bc10400c7`；
原 full upstream log SHA256：
`451e37239eb15a1ebeb929eed9eea66eb2e37159c754cc5649cd11f0faeb5c11`。
唯一 launch、完整 WAL/receipt chain、release/postrelease 与自有进程0已核验。
不是49/49、当前 HEAD 平台 CI、正式发布或提审通过。上面的旧 r006/r008/r013
属于历史范围，不替代本次证据；r009/r010 的原失败保留，不重解释为通过。

由于当前测试账户未具备原测试所需的具名账户、tty组、root及跨UID受控条件，
相关测试暂不具备完整执行权限。保留原分母和实际 ERROR/SKIP，供具备条件的
环境补充验证；不模拟账户、不弱化认证，也不把未知软件失败列入此说明。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7d9d51d7c72f92e58943d44fff11ee5f7a40f8458e0d594178f0d13f85ee604b
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：4f392c3370864e7bf78843fbd7ef0368f7c54fa742e0973ed3ce892d80795911
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e3b1a2902ce600ac9f24af5f58c8a8622301edba66d15c1356d87486c1ccfb0d
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：e3b1a2902ce600ac9f24af5f58c8a8622301edba66d15c1356d87486c1ccfb0d
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：48a3ff5db91c737e959d75b5151f09ee4b95f05da69188bb037c59e543e19810
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：48a3ff5db91c737e959d75b5151f09ee4b95f05da69188bb037c59e543e19810
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：48a3ff5db91c737e959d75b5151f09ee4b95f05da69188bb037c59e543e19810
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：48a3ff5db91c737e959d75b5151f09ee4b95f05da69188bb037c59e543e19810
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：6b452ee7c9c036f4bf269d6cf686d790b836874b41288bfa2851ba9b8aba2d62

### 当前 r960：实际 worker 路径的精确能力分类修复

平台 build97642 的实际源码诊断采用 `storage/Users/currentUser/.cache/conan2`
前缀，而非私有 `conan-home`。仅补充这个精确前缀，继续核对原源码行、
当前 UID 与完整 NSS 错误；未放宽认证、未知错误或原上游断言。

同一全新事务 r960 官方 step35/Conan create RC0；原49组全部执行，44clean、
1partial、3ERROR、1wholeSKIP。消费者4/4，鸿蒙专项1/1；完整 WAL/receipt
chain、唯一 launch、自有进程0及 release/postrelease 已独立核验。
observer SHA256：`c81c8ce6d0c352550a152c19cbd6880c2919fe432c533e436f11aedc6292f854`；
原 full upstream log SHA256：`ea9e5e95e9a9934a9e562407704a2c22b9f7896de819e13c6368161c1c2c20a5`。
当前账户未具备原具名账户、tty组、root与跨UID受控条件，相关权限限制仍
保留实际 ERROR/SKIP 及原分母。不是49/49或当前提交平台 CI、发布、提审通过。

- 能力例外：dbus - dbus:bus/named-tty-group；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：9418f74aec6b565419e8b3906057056e8fa29c54f72224324b856c5324984ab5
- 能力例外：dbus - dbus:misc-internals/current-username-uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：89b7a7891216c588a39d01d2f756aa94d02f872efdcd09295aad63e336220791
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/session；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：daf22796604712a682bd2ae37dcb4bc762383923a315cc0582fc95607690e188
- 能力例外：runs-dbus-daemon+slow - dbus:dbus-daemon//fd-limit/system；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：daf22796604712a682bd2ae37dcb4bc762383923a315cc0582fc95607690e188
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/uae/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：8843b2c1e7207af34fd44d132494a498eaa34d5d1e7f6fa31cdf8ec69a76fe62
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/root；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：8843b2c1e7207af34fd44d132494a498eaa34d5d1e7f6fa31cdf8ec69a76fe62
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/messagebus；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：8843b2c1e7207af34fd44d132494a498eaa34d5d1e7f6fa31cdf8ec69a76fe62
- 能力例外：runs-dbus-daemon - dbus:uid-permissions//uid-permissions/monitor/other；结果：SKIP；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：8843b2c1e7207af34fd44d132494a498eaa34d5d1e7f6fa31cdf8ec69a76fe62
- 能力例外：dbus - dbus:userdb//userdb/groups_from_uid；结果：ERROR；原因：ACCOUNT_PRIVILEGE_UNAVAILABLE；证据：7bd88e715820e90d832f950bf8067a3d6b1966a153480e5a776100e1ad5e7e6a
