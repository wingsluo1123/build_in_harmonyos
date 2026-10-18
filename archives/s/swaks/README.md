# swaks

`swaks`（Swiss Army Knife for SMTP）是一个用 Perl 写的 SMTP 事务测试工具，用于构造、调试和脚本化
SMTP 会话：支持 SMTP/ESMTP/LMTP、TLS、多种认证方式、socket/UNIX socket/管道三种传输方式，并且
选项可以来自命令行、环境变量和配置文件。

上游把它设计成"面向事务、可脚本化"的调试工具，因此它在下游常被用作邮件服务、反垃圾、网关和
TLS 配置的验证客户端。

## 功能

- 完整的 SMTP 事务控制：`--helo`、`--from`、`--to`、`--header`、`--body`、`--quit-after` 等。
- 多种传输方式：`--server host:port`（TCP）、`--socket <path>`（UNIX socket）、`--pipe <cmd>`（管道）。
- TLS 与会话调试：`--tls`、`--tls-verify`、`--tls-chain`、`--tls-get-peer-chain` 等（依赖 `Net::SSLeay`）。
- 认证支持：AUTH PLAIN/LOGIN/CRAM-MD5/CRAM-SHA1/NTLM/DIGEST-MD5（按可用模块降级）。
- `--support` 打印当前解释器下各特性/模块的可用性矩阵，便于定位环境缺什么。

## OpenHarmony 适配

- 包形态：`package_type = "application"`，只交付 `bin/swaks` 一个可执行入口；`package_info()` 里
  显式清空 `libdirs`/`includedirs`/`libs`，避免被下游当作库消费。
- 解释器依赖：脚本需要一个 Perl 5 解释器，而 OHOS 默认不提供 `perl`。本配方把
  `perl/5.42.2` 声明为运行时依赖（`self.requires("perl/5.42.2", run=True)`），
  这样 `conan install` 生成的 `conanrun` 环境会把 `perl` 与 `swaks` 一起放进 `PATH`，
  而不是依赖使用者自己装解释器。
- 无补丁：上游首行已经是 `#!/usr/bin/env perl`，鸿蒙 HongMeng Kernel 1.12.0 起
  `/usr/bin/env` 存在（E037），可直接运行；这一点由消费测试显式断言。
- 构建期身份校验：`build()` 不编译任何东西，但会校验脚本内的版本标记与 shebang，
  防止"打包了错误的上游资产"被静默放过。
- 消费测试：`test_package/mock_smtp.pl` 是一个只用核心模块写的极简 SMTP sink，
  测试驱动 `bin/swaks` 与它完成真实 ESMTP 事务（含 `DATA` 与结尾点、`QUIT`），
  并断言会话记录；另有"RCPT 被 550 拒绝时 swaks 必须非 0 退出"的反向场景。

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| `perl` | 5.42.2 | 运行时（`run=True`） | 脚本解释器；ohpcd 上的 OHOS 制品包已核实包含 `Pod::Usage`、`File::Spec::Functions`、`IO::Socket::IP`、`IPC::Open2` 等 swaks 需要的模块 |

已核实的可选特性缺口（ohpcd 上的 OHOS perl 包未提供对应模块，`swaks --support` 会如实报告，
缺失不影响 SMTP 主流程）：

- `Net::SSLeay`：TLS / STARTTLS（`--tls*`）不可用。
- `Net::DNS`：MX 路由不可用。
- `Authen::NTLM`、`Authen::SASL`：NTLM / DIGEST-MD5 认证不可用。

AUTH PLAIN/LOGIN（`MIME::Base64`）、CRAM-MD5/CRAM-SHA1（`Digest::MD5`/`Digest::SHA`）、
socket 与 `--pipe` 传输、UNIX socket 传输所需模块均在包内。

## 上游测试

官方发布资产 `swaks-20240103.0.tar.gz` 只包含脚本、README、LICENSE 和 `doc/`，**不含测试**；
但上游仓库本身有完整回归套件，位于 `testing/`（需从 tag 归档获取）：

- 用例：`testing/regressions/<group>/*.test`，共 **2,589 例 / 12 组**（另有 7,718 个 `out-ref/` 期望文件）
- 驱动：`testing/regressions/bin/run-all.pl`（headless）/ `bin/run-tests.pl`
- 测试服务器：`testing/server/smtp-server.pl`（`_exec-transactions` 等组依赖它）

OHOS 实测（包内 `bin/swaks`，2026-10-17 全量）：

| 项目 | 结果 |
|------|------|
| 执行 | **2,589 例**（12 组全部执行，无未执行组；耗时 453s） |
| 通过 | **2,133**（**82.39%**） |
| 失败 | 455 |
| 跳过 | 1（上游标注 Windows-only） |

首轮对照（2026-10-15，`_exec-transactions` 因缺 `Net::SSLeay` 无法执行）：2,354 例 / 1,667 pass（70.8%）；
在**两轮都执行的 2,353 例**上，通过 1,667 → 2,005（**70.8% → 85.2%**）。

`Net::SSLeay` 阻塞已解除：设备上手工编译 `Net::SSLeay` 1.96（静态链接 ohpcd 的 OHOS OpenSSL 3.5.8，
**真实现非桩**）后，`swaks --support` 报 `=== TLS supported`，`_options-tls` **252/252** 通过，
`_exec-transactions` **首次执行 235 例**（122 pass）；`Socket6` 0.29 同样是手工编出的真实现，
装好后 `swaks --support` 16 行全部 supported。

剩余 455 例归因（可重叠）：**418 例（92%）**是 harness 的 hostname munge 环境差异（设备 hostname 恰为
`localhost`，被替换成 `LOCAL_HOST_NAME`，而上游 ref 是字面 `localhost`，非 swaks 缺陷）；**缺可选模块类
失败已降为 0**（`IO::Socket::INET6` 也手编成真实现，`swaks --support` 16/16 全 supported）；4 例 TLS 残留；
19 例未归因。详细清单与运行证据见 `20240103.0/manifest.yaml` 与 `20240103.0/test_package/MANIFEST.yml`。

结论：上游套件在 OHOS 上**全量跑通 82.39%**，阻塞项已用真实现解除；剩余失败绝大多数是 harness 环境
差异与该 perl 包的遗留问题，不是 swaks 配方缺陷。

## 参考

- 上游主页: https://jetmore.org/john/code/swaks/
- 上游源码: https://github.com/jetmore/swaks
- 官方发布资产: https://github.com/jetmore/swaks/releases/download/v20240103.0/swaks-20240103.0.tar.gz
- 上游官网同源副本: https://www.jetmore.org/john/code/swaks/files/swaks-20240103.0.tar.gz
- Homebrew 公式: https://formulae.brew.sh/formula/swaks
