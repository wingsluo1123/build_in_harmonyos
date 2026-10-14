# cvm

CVM（Credential Validation Modules）提供统一的凭据校验客户端、模块协议、传输库和命令行程序，可将认证请求转发给命令、Unix socket 或 UDP 模块。

## OHOS 适配

- 使用上游 SPAC/Makefile 流程，但由 Conan 生成 `conf-cc`、`conf-ld`、`conf-lib`，避免裸编译器和宿主库路径进入目标包装器。
- 交付 9 个共享库、13 个命令和公共头文件，并提供细粒度 CMake 组件（例如 `cvm::v2client`、`cvm::module`、`cvm::udp`）。
- 修复命令传输第二次 `pipe()` 失败后仍进入 `fork()` 的错误，并用确定性故障注入及真机资源限制测试覆盖回退路径。
- 运行全部 52 个上游命名测试（76 次实际比较），以及公共 API、资源耗尽、包内命令和 22 个交付 ELF 的消费者审计。

## 依赖

- `bglibs/2.04`：公共数据结构、口令比较和 vmailmgr 支撑库。
- `libtool/2.5.4`：构建期生成和链接共享库。
- `sqlite3/3.49.1`、`cdb/20251021`：仅用于补齐上游测试夹具，不进入 CVM 公共依赖闭包。

## 版本

- `0.97`：HarmonyOS PC / AArch64，状态 `built`。

## 参考

- [CVM 官方主页](https://untroubled.org/cvm/)
- [CVM 官方源码仓库](https://github.com/bruceg/cvm)
