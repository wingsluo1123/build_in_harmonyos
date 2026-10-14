# libcontentaction 0.4.13 — 真机（DAYU200-RK3568）E2E 证据

> 本节数字全部来自 **2026-10-09 08:52（+08:00）在唯一真机上真实执行**的一次运行，
> 原始日志见同目录 `device-e2e-both-phases.log`，执行器回执见 `device-evidence.json`。

## 1. 运行环境（实测）

| 项 | 值 |
|---|---|
| 设备 | DAYU200-RK3568，`serial=450100445634303332018f3e7d2dba00` |
| 系统 | `OpenHarmony 6.0.0.47`（API20, aarch64, 64bit） |
| 执行器 | `automation/device_runner.sh`，job=`lca_r26` |
| 资源租赁 | resbroker `lease_id=38c2c2f60d9e`，`queued_s=0.0`，`duration_s≈9.0` |
| 退出码 | **`exit_code=0`**（`result_json_received=true`） |

## 2. 被推送并执行的产物（sha256 实测）

| 产物 | sha256 | 类型 |
|---|---|---|
| `test_lca_consumer` | `14b437635d1e4fa41ced44f7aa606d406f04a834ce3b72a74ac8bbfa91f34ca4` | `ELF 64-bit LSB pie executable, ARM aarch64` |
| `libcontentaction6.so.0.4.13` | `ab0ba0f72cf88a10b983168fcf21d6dc513210bc0f1c35c4066ab3b20eb0e96b` | `ELF 64-bit LSB shared object, ARM aarch64` |

推送结果：`pushed 46/46 files -> /data/local/tmp/ohpc_test/lca_r26`。

> 说明：mime 数据库是**嵌套目录**，而执行器只推送**扁平文件**，
> 因此打包为单个 `mimedb.tar` 并在设备侧 `tar xf` 解出后作为 `argv[2]` 传入。
> 这样做之后，先前因缺库而被跳过的 `typeDescription` 断言得以**真实执行并通过**
> （`INFO: typeDescription(text/plain) = 'Plain text document'`）。

## 3. 结果（两阶段，实测）

| 阶段 | 命令（设备侧） | 结果 |
|---|---|---|
| 阶段 1（主用例，全新数据区） | `./test_lca_consumer ./lca-consumer-work ./mimedb` | **`RESULT: 26 checks, 0 failures`**，`__RC1__=0` |
| 阶段 2（新进程复核默认值回落） | `./test_lca_consumer ./lca-consumer-work ./mimedb check-default` | **`RESULT: 3 checks, 0 failures`**，`__RC2__=0` |

合计：**29 checks，0 failures**。

## 4. 覆盖到的行为（真机实测断言）

- **ContentInfo**：`forMime(text/plain)` 有效性、`mimeType()==text/plain`、
  `typeDescription()` 走 shared-mime-info 库得到 `Plain text document`、`forFile(note.txt)` 类型识别。
- **默认动作**：`defaultActionForFile(note.txt)` 有效且 `name()==consumer-viewer`、`Action::icon()` 取自 Desktop Entry、
  `actionsForFile()` 非空。
- **默认值往返**：`setMimeDefault` → `defaultActionForMime` 往返得 `consumer-mailer`；
  `mimeapps.list` 在 `resetMimeDefault` 后仍可读（**不静默通过**）；`resetMimeDefault` 确实移除映射。
- **协议**：`defaultActionForScheme(mailto:) == consumer-mailer`。
- **高亮**：`findHighlights()` 恰好 1 段、覆盖邮件地址、`findNextHighlight()` 返回同段；
  `highlight()` 产出带可用 action 的 Match 且映射到 `consumer-mailer`。
- **触发**：`trigger()` 真实执行 Desktop Entry 的 `Exec`（生成并校验 marker 文件内容）。
- **跨进程回落**：全新进程下用户默认已清空、`*ForFile` 回落 `mimeinfo.cache`、scheme 仍解析到 `consumer-mailer`。

## 5. 与本地 QEMU 复核的一致性

本地 `conan create`（profile `ohos-aarch64-run`，QEMU 执行）在同一 HEAD 上得到
阶段 1 `26 checks, 0 failures`、阶段 2 `3 checks, 0 failures`，
与真机结果**逐项一致**（见 `local-qemu-consumer-both-phases.log`、`ctest-qemu-summary.txt`）。

## 6. 诚实说明

- 真机运行期间设备被多任务排队占用，本次为**取得租约后**的真实执行，非模拟、非复用旧日志。
- 未做任何"构建成功即视为测试通过"的替代；上表全部为**设备上真实打印**的断言计数。
- 上游 ctest 为 `100% tests passed, 0 tests failed out of 15`（11 Passed + 4 Skipped，
  跳过项为环境预检 `SKIP_RETURN_CODE=77`），本文件不将其记作"15 项全部执行"。
