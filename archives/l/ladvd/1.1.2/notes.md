# ladvd 1.1.2 适配笔记

## 编译环境

- 目标：HarmonyOS PC / AArch64
- 构建系统：Autotools
- 编译器：Clang 15
- 构建类型：Release
- 状态：built；本地真机构建及测试完成，发布状态以官方 CI 和制品仓为准

## 构建方法

配方下载官方 `v1.1.2` 源码并严格校验 SHA256，应用十个可审查补丁，
再覆盖经过同一补丁集生成的 Autotools 文件。Conan 通过
`AutotoolsToolchain` 注入目标编译器和依赖，并使用：

```text
--build=aarch64-unknown-linux-gnu
--host=aarch64-unknown-linux-ohos
--with-systemdsystemunitdir=no
```

构建过程先编译主程序，再显式编译、签名并执行全部上游测试程序；安装后
对 `ladvd` 重新签名并验证 `.codesign` 节数量。

## 问题与处理

| 问题 | 根因 | 处理 |
|---|---|---|
| `configure` 不识别目标 | 上游只接受 Linux/BSD canonical host | 将 `linux-ohos` 映射到已有 Linux 网络后端 |
| `MAXPATHLEN` 未定义 | HarmonyOS 提供 `PATH_MAX`，不提供 BSD 别名 | 缺失时从 `PATH_MAX` 定义 `MAXPATHLEN` |
| Release 测试出现未初始化指针/崩溃 | 上游把赋值放在 `assert()` 中，`NDEBUG` 会连同副作用一起删除 | 赋值移到断言之前，并保留断言和显式空值处理 |
| `check_util` 日志函数名期望不符 | 新版 Check 将测试函数展开为 `*_fn` | 由 `__func__` 生成期望值，不改业务断言 |
| `check_child` 把预期 SIGTERM 记为测试错误 | HarmonyOS 上 Check 会观察到嵌套 helper 的信号退出 | helper 捕获 SIGTERM 后以成功状态退出，并显式检查 `fork()` 成功；测试断言不变 |
| 原生 `autoreconf` 在存储目录失败 | HarmonyOS 存储文件系统上的 `getcwd`/临时目录行为不兼容；粗粒度时间戳还可能让 `make` 误判 `configure.ac` 较新并重新生成 | 在宿主生成并随配方导出 Autotools 文件；构建时先完成 `configure` 改写，再统一刷新全部生成文件时间戳，禁止 `make` 重新进入 Autoconf |
| `config.status` 写 `conf*/subs1.awk` 被拒绝 | Autoconf 的 `mktemp -d` 强制创建 mode-0700 目录，部分 HMDFS Worker 的所有者映射使创建进程也无法写入 | 复用 E011 所述根因，并采用 E112/E114 已记录的绕过 `mktemp` 技术：将临时目录改为逐进程命名的普通 `mkdir`，且对改写结果失败关闭；不把该既有机制申报为路径 B |
| Check 无法创建临时文件 | `/tmp` 对构建用户只读，且 Check 优先读取 `TEMP` | 同时设置 `TEMP` 和 `TMPDIR` 到私有可写目录 |

## 补丁范围

- `0001`、`0002`：目标平台识别和头文件可移植性。
- `0003`–`0008`：修复 Release/NDEBUG 下被删除的副作用赋值。
- `0009`：让嵌套测试 helper 正常退出并验证 `fork()` 成功。
- `0010`：兼容当前 Check 框架生成的测试函数名。

`0010` 同时形成路径 B 知识候选 E14861。Check 0.12.0 把
`START_TEST(test_my)` 展开成 `test_my`，0.13.0 起改成内部符号
`test_my_fn`；逻辑用例名没有变化。旧测试把内部符号硬编码到日志预期，依赖
升级后即产生假失败。补丁从当前 `__func__` 构造自反预期，完整字符串比较仍
保留。三臂证据、查重边界与真机日志哈希见
`reports/path-b-evidence.md`。

补丁没有删除测试、降低断言或用平台宏绕过失败。

## 知识积累

- ✅ `E14861-draft-7A1D`：Check 0.13 重写 `START_TEST` 后改变了宏生成的
  内部 C 函数名；自反日志测试应由当前 `__func__` 构造预期，不能硬编码框架
  私有符号。真机原始失败、正确修复和完整回归已记录并哈希绑定。

## 依赖

- 运行/构建：`libevent/2.1.13`、`libpcap/1.10.6`
- 测试：`check/0.15.2`

## 验证

- 上游：7 个 Check 可执行文件、45 个 `START_TEST` 用例，全部由
  `make check -j1` 在 HarmonyOS PC 真机执行。
- 包级：从被测 Conan 包的绝对 `bin` 路径执行 `ladvd -h` 与
  `ladvdc -h`，并执行 1 个鸿蒙特有端到端消费者用例：以
  `ladvd -d -o -s -L` 驱动已安装且已签名的真实程序完成初始化、特权分离
  进程创建、目标接口发现、Ethernet pcap 流头输出和父子进程正常退出。
  该消费者流程是 1 个完整用例，其命令入口与流程结果由 13 个辅助断言校验；
  断言数不作为鸿蒙特有用例数。
- 能力探针：真机同时支持 `AF_UNIX/SOCK_SEQPACKET` 与
  `AF_UNIX/SOCK_STREAM`。因此没有构造不存在的 fallback 故障，也不以此
  申报路径 B。

## 交付物

- `bin/ladvd`
- `bin/ladvdc`（指向 `ladvd` 的命令入口）
- `licenses/LICENSE`
---

**编译结束**: 2026-10-13 13:51
**最终状态**: built
