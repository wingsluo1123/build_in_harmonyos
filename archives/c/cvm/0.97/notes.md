# cvm 0.97 适配笔记

## 构建与依赖

- 上游构建系统是 SPAC 风格 Makefile：`conf-cc`、`conf-ld` 和 `conf-lib` 动态生成 `compile`、`load`、`ltcompile`、`ltload`、`makeshlib`。
- 配方从 Conan `AutotoolsToolchain.vars()` 取得编译器、编译参数与链接参数，并显式加入 `bglibs/2.04` 的头文件和库目录；`libtool/2.5.4` 仅作为构建工具。`sqlite3/3.49.1` 与 `cdb/20251021` 仅作为上游测试夹具，不进入公共依赖闭包。
- 包交付 9 个共享库、13 个上游安装清单中的命令、公共头文件以及兼容头 `cvm/client.h`、`cvm-sasl.h`。静态归档不交付，避免同一包同时宣称两种链接模型。
- Libtool 的未安装命令会把临时库目录写入 `DT_RUNPATH`，依赖归档还会把缓存路径带入 DWARF。配方以稳定 `/usr/lib` 生成 Libtool 元数据，并对 9 个真实共享库和 13 个命令统一去调试信息、清除 RPATH、移除旧签名和重新签名。消费者逐个验证无私有路径、SONAME 链、NEEDED 闭包以及签名数量。该处理复用 DRAFT-7324/E236，不作为新增 B 类知识。
- `bglibs` 是公共头和链接接口的一部分，使用 `transitive_headers=True`、`transitive_libs=True` 并由各 CMake 组件显式声明依赖。

## 修复

`client_xfer_command.c` 原代码把第二次 `pipe()` 的失败值写成 `-2`。实际 API 只返回 `-1`，因此部分资源获取失败后仍会进入 `fork()`，并使用未初始化的第二组描述符。补丁将两次获取拆开：第二次失败时关闭第一组 pipe；`fork()` 失败时关闭两组 pipe。

黑盒 `RLIMIT_NOFILE` 测试可验证修复后的外部结果，但上游错误路径含未定义状态，不能可靠区分回退版本。为避免假绿，构建期回归测试对本编译单元替换 `pipe`、`fork` 和 `close`，覆盖四种状态：第一次 pipe 失败时无后续副作用；第二次失败时第一组两个 fd 各关闭一次；fork 失败时两组四个 fd 各关闭一次；父进程成功时只关闭 10、21，并向调用者交付 11、20。恢复上游 `-2` 判断后，同一矩阵稳定失败。

## 上游测试

上游 `tests.sh` 定义 52 个唯一测试名和 76 次 `run_compare_test` 调用。完整套件需要 `sqlite3/cvm-sqlite`、`cdbmake/cdbget` 与脚本自建的 Qmail/vmailmgr 账户数据；AF_UNIX 和 UDP transport 由当前项目自身启动。

配方以 Conan test requirements 提供 sqlite3、cdbmake/cdbget，并构建仅供测试的 `cvm-sqlite`。HarmonyOS 的数值 UID 在 passwd 数据库中无映射，脚本因此使用配方通过 Python `os.getuid()/os.getgid()` 注入的真实数值；`/storage` 挂载点拒绝 pathname AF_UNIX，而 `/data` 缓存挂载点支持，配方以真实 `bind()` 探针选择测试临时目录。`vmailmgr-xconvert` 的黄金字节保持不变，只规范化不同 `xxd` 版本的偏移栏宽度。最终 52 个名称、76 次比较全部执行，结果为 `76 tests executed, 0 failures`。

## 消费者与真机验证

- CMake 消费者通过 `cvm::v2client` 编译并调用账户拆分与错误字符串 API，验证 CVM 与 bglibs 的传递头文件/库信息。
- `RLIMIT_NOFILE=5` 运行时测试验证真实共享库在第二个 pipe 无法分配时返回 `CVME_IO`，且没有执行辅助模块。
- 命令测试使用包内绝对路径运行 `cvm-testclient` 和 `cvm-pwfile`，对正确口令检查 UID/GID/目录输出，对错误口令检查退出码 100 与 `Credentials rejected`。
- ELF 审计覆盖 9 个共享库和 13 个命令，共 131 项断言：有效 RPATH/RUNPATH 为空、原始字节无个人/Conan 缓存路径、SONAME 与链接链闭合、全部 NEEDED 可解析，并确认每个重签命令恰有一个 `.codesign`。
- 真机环境：HarmonyOS 6.0、AArch64、Clang 15.0.4、Conan 2.29.1；完整 `conan create` 已通过。

## 已知环境现象

OHOS 存储层对部分父目录的 `getcwd()` 会产生诊断，并且 pathname AF_UNIX 能力依赖挂载点。上游测试通过显式 `CVM_TEST_SOURCE` 指向构建产物、从 `/` 启动测试 shell，并把临时夹具放到探针确认可用的目录，避免诊断污染逐字节期望输出；这属于既有 E386 类环境约束，不作为本任务新增知识申报。

## 最终状态（结束标记）

编译结束：真机 `conan create`、全部 52 个上游名称（76 次比较）、四场景确定性回归矩阵及 4 组 `test_package` 均通过。本地验证已完成；官方 CI、审核、合入和 release 发布状态以 PR 及制品仓最终结果为准。
---

**编译结束**: 2026-10-13 13:47
**最终状态**: built
