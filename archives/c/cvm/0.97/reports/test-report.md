# cvm 0.97 测试报告

## 结论

cvm 0.97 已在 HarmonyOS PC AArch64 真机完成一次完整、干净的 `conan create`。配方构建并打包 9 个共享库和 13 个上游命令；全部上游测试、失败原子性回归测试及包后消费者测试均通过。

| 测试层 | 结果 |
|---|---:|
| 上游声明的命名测试 | 52 |
| 上游 `run_compare_test` 调用 | 76 |
| 本环境执行的上游命名测试 | 52/52 PASS |
| 本环境执行的实际比较 | 76/76 PASS |
| 未选择的命名测试/调用 | 0/0 |
| 确定性四场景资源状态矩阵 | 4/4 PASS |
| 恢复上游错误后的破坏性负测 | 预期失败，退出码 2 |
| `test_package` 测试组 | 4/4 PASS |
| `test_package` 集成断言 | 19/19 PASS |
| `test_package` OHOS ELF/签名断言 | 131/131 PASS |
| `test_package` 断言合计 | 150/150 PASS |

赛事 PR 统计以“独立可失败的比较/断言点”为单位，不把未执行的上游比较计为通过：

| 测试类型 | 数量 | 构成 |
|---|---:|---|
| 单元测试 | 80 | 76 次上游比较＋4 个确定性故障场景 |
| 集成测试 | 19 | CMake 消费者、安装后资源耗尽、包内命令的独立断言 |
| 鸿蒙特有测试 | 131 | 22 个 OHOS ELF 的 RPATH、路径泄漏、SONAME、NEEDED 和 `.codesign` 断言 |
| **合计** | **230** | 其中新增验证 154 项：150 个 `test_package` 断言＋4 个故障场景 |

## 环境

- 系统：HarmonyOS 6.0，AArch64
- 编译器：Clang 15.0.4，libc++，C/C++17 消费者环境
- 包管理器：Conan 2.29.1
- 运行库依赖：`bglibs/2.04`
- 构建工具依赖：`libtool/2.5.4`
- 上游测试夹具依赖：`sqlite3/3.49.1`、`cdb/20251021`
- 配置：`shared=True`

## 上游测试

上游 `tests.sh` 定义 52 个唯一测试名、76 次 `run_compare_test` 调用。本次在 OHOS 真机完整执行全部 52 个名称、76 次原始比较，包括：

- pwfile/command 传输及正确、错误凭据；
- `lookup` 与 `v1lookup` 的有密钥/无密钥组合；
- SQLite、`sql-query-test` substitution、Qmail/vmailmgr、chain 与 split 用例；
- SASL LOGIN、PLAIN、EOF 与错误路径；
- AF_UNIX 与 UDP transport 的启动、v1/v2 认证、拒绝及停止序列。

结果为 `76 tests executed, 0 failures`，没有把未执行项计为通过。`sqlite3` 和 `cdbmake/cdbget` 来自已发布的 Conan test requirements，不进入 CVM 的公共依赖闭包；`cvm-sqlite` 使用由 Conan 包目录生成的 `sqlite.lib`，不再引用宿主 `/usr/lib/sqlite`。上游脚本在 HarmonyOS 的数值 UID 无 passwd 映射时使用配方注入的真实 UID/GID，并把临时夹具放到经过实际 `bind()` 探针确认支持 pathname AF_UNIX 的挂载点。`vmailmgr-xconvert` 仍逐字节验证 cdb 内容，只将当前 `xxd` 的 8 位偏移栏规范化为上游期望的 7 位显示。

## 缺陷复现与回归闭环

上游 `client_xfer_command.c` 将第二次 `pipe()` 的失败条件错误写为 `== -2`，而 POSIX `pipe()` 失败返回 `-1`。确定性编译单元测试替换该文件使用的 `pipe`、`fork` 和 `close`，记录完整调用序列。

- 第一次 pipe 失败：仅调用一次 pipe，不 fork、不 close。
- 第二次 pipe 失败：不 fork，第一组 10、11 各关闭一次。
- fork 失败：按逆序先关闭第二组 20、21，再关闭第一组 10、11。
- 正常父进程：关闭 10、21，向调用者交付 11、20。
- 临时恢复上游判断：同一矩阵稳定失败，证明负测对回退敏感。

另有包后黑盒测试对真实共享库设置 `RLIMIT_NOFILE=5`，验证返回 `CVME_IO` 且辅助模块未执行。该黑盒结果用于验证交付产物，但不单独作为回退判据，因为错误版本的未初始化状态可能偶然产生同一最终错误。

## 包后消费者测试

1. CMake 消费者链接 `cvm::v2client`，验证公共头、传递的 bglibs 接口、账户拆分和错误字符串，共 5 个独立断言点。
2. 真实包内共享库在文件描述符耗尽条件下验证第二个管道失败路径和无子模块副作用，共 2 个独立断言点。
3. Python 驱动以 Conan 包对象提供的绝对目录运行 `cvm-testclient` 与 `cvm-pwfile`，验证包内命令集、无 RUNPATH、正确凭据输出以及错误凭据的退出码 100 和拒绝文本，共 12 个独立断言点。
4. 以上三组合计 19 个集成断言点；独立 ELF 审计对 9 个共享库和 13 个命令执行 131 个 OHOS 交付断言点：RPATH/RUNPATH 为空、原始 ELF 字节无 `.conan2` 或个人路径、SONAME/真实文件/软链接链正确、NEEDED 可由包/依赖/系统闭合，且 13 个命令各有且仅有一个 `.codesign`。两类共 150 个断言点。

## 证据绑定

- 正式 W3 由 `ohc-run.py finish` 在真机生成，回执 `exit_code=0`，日志 SHA256 为 `24a114d1997b7edd78b65eb2af5dc4cb81a68f06387e360f777c0b502f4ab611`。
- 正式 W3 日志明确记录 `76 tests executed, 0 failures`，并通过 L1 上游测试、`test_package` 执行和破坏性负测门禁；运行时 `.ci-result.json` 与日志不作为仓库文件提交。
- 测试输入、回归源码和期望均位于本版本目录，可由同一配方重新执行。

## 已知限制

- 上游 52 个测试名、76 次比较已全部执行；sqlite/cdb 仅为测试夹具依赖，不随 CVM 包传播。
- SPAC/Libtool 包装器的交叉工具链配置复用既有 `DRAFT-7324-BGLIBS-DJB-TWO-STAGE-CROSS-BUILD`，不是本次 B 类新增知识。
- 本次新增知识仅申报“多资源分阶段获取在不可逆副作用前的失败原子性，以及确定性故障注入与真实产物资源耗尽的双层验证”。
