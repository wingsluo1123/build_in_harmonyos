# GNU Mailutils 3.20 — HarmonyOS 真机测试报告

## 测试环境与来源

- 上游源码：GNU 官方 HTTPS `https://ftp.gnu.org/gnu/mailutils/mailutils-3.20.tar.xz`。
- 源码归档 SHA-256：`a8f3faab1edda5188bb5ca3e4e9c0c5bc72cd0dadf4e1f4799d27fa75c6ae829`；设备端校验通过，`xz -t` 通过。对应 `.sig` 已下载，但设备和本机均无 `gpg`/`gpgv`，未能验签。
- 目标设备：HarmonyOS PC，aarch64；经 PC → amax → 设备 SSH 2200 反向隧道执行。
- Conan：`CONAN_HOME=/storage/Users/currentUser/work/psj/ch-mailutils`；Conan package storage 使用 `/data/storage/el2/base/cache/mailutils-8661-r6/p`，避开 HMDFS 不保留 chmod 语义的问题。
- 本次运行 `mailutils-15271-20261017-r1` 在 `/data/storage/el2/base/cache/mailutils-3.20-nvdqbud4` 创建 native workspace；配方先验证 `mkfifo` 可用，再复制已打补丁的源码并在该 workspace 运行 configure、编译和上游测试。`TMPDIR`、`TMP`、`TEMP` 均指向 workspace 内目录。
- 上游命令：`make -j2 -k check`。统计按各 Autotest suite 的原始 `testsuite.log` 汇总；未运行的 DejaGNU harness 不计入分母。

## 上游用例汇总

**21 个实际执行并生成 summary 的 Autotest suite，共 1,389 项：1,389 通过、0 失败、0 跳过（100%）。**

| suite | 总数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| `comsat/tests` | 7 | 7 | 0 | 0 |
| `frm/tests` | 10 | 10 | 0 | 0 |
| `imap4d/tests` | 107 | 107 | 0 | 0 |
| `libmailutils/tests` | 739 | 739 | 0 | 0 |
| `libmu_auth/tests` | 1 | 1 | 0 | 0 |
| `libproto/dotmail/tests` | 23 | 23 | 0 | 0 |
| `libproto/maildir/tests` | 19 | 19 | 0 | 0 |
| `libproto/mailer/tests` | 3 | 3 | 0 | 0 |
| `libproto/mbox/tests` | 15 | 15 | 0 | 0 |
| `libproto/mh/tests` | 14 | 14 | 0 | 0 |
| `libtests` | 12 | 12 | 0 | 0 |
| `mail/tests` | 22 | 22 | 0 | 0 |
| `mda/lmtpd/tests` | 2 | 2 | 0 | 0 |
| `mda/mda/tests` | 4 | 4 | 0 | 0 |
| `mda/putmail/tests` | 2 | 2 | 0 | 0 |
| `messages/tests` | 4 | 4 | 0 | 0 |
| `mh/tests` | 270 | 270 | 0 | 0 |
| `mimeview/tests` | 21 | 21 | 0 | 0 |
| `readmsg/tests` | 6 | 6 | 0 | 0 |
| `sieve/tests` | 105 | 105 | 0 | 0 |
| `testsuite` (auxiliary tools) | 3 | 3 | 0 | 0 |
| **合计** | **1,389** | **1,389** | **0** | **0** |

发行包有 22 个 `testsuite.at` 源文件。`libmu_scm` 的 Guile suite 不属于默认 `make check` 目标；`mail` 与 `pop3d` 的 DejaGNU harness 因设备没有 `runtest` 未执行，这些 harness 不在上述 1,389 项分母内，也未被记作 skip。

## Conan `test_package`

真机 Conan `create` 退出码为 **0**。该次运行在同一候选中通过上游完整 gate 并安装、消费生成的包：

- 消费者 API：CTest `mailutils_api` 1/1；`mu_list`、`mu_url`、`mu_locker` 与文件安全 API 共 14/14 断言。
- HarmonyOS 专项：24/24 检查通过，覆盖平台/架构、客户端与服务端文件、版本和共享库。
- 邮件流端到端：6/6 检查通过；`putmail` 创建邮箱并投递，再由 `mail` 与 `readmsg` 读回主题和正文。

## 本次运行证据

- 上游结果 JSON：`/data/storage/el2/base/cache/mailutils-8661-r6/p/b/mailu425e8b7afd356/b/build-release/upstream_test_result.json`；SHA-256 `703bb6181259b53cad371597423a0af12bd6e50d1d36dcc07686702249d58264`。记录 `total=1389, passed=1389, failed=0, skipped=0, suite_count=21`。
- 上游原始日志：`/data/storage/el2/base/cache/mailutils-8661-r6/p/b/mailu425e8b7afd356/b/build-release/upstream-make-check.log`；SHA-256 `2b7ae4e77ff5a9010c2cb5620b70268429e60e1104a0d6a8a8eaa2e64ada0699`。
- 完整 Conan 设备日志：`/storage/Users/currentUser/work/psj/ch-mailutils/mailutils-15271-20261017-r1.log`；SHA-256 `d63e70665a989e499744f4c8b7a50294070dfcbb891ecac5709ea6e3d1172440`；退出码 0。
- 消费者 CTest `mailutils_api`：1/1 test passed，14/14 检查通过；`LastTest.log` SHA-256 `cef9b5eccf6ccfbf25fece9aee0e5ad457759ab32ff3a73d5a1ce24514443b42`。
- HarmonyOS 专项 24/24，邮件流 E2E 6/6；完整 `conan create` 输出 `CONAN_CREATE_EXIT=0`。

## 设备安装权限边界

上游安装钩子尝试对 `sbin/mda` 执行 `chown root:mail` 后设置 setuid；当前设备没有 `chown`，该错误被上游 Makefile 忽略。包内 `sbin/mda` 实际权限为 `750`，不带 setuid，因此需要 root 权限的本地投递场景未由本次消费者检查覆盖。
