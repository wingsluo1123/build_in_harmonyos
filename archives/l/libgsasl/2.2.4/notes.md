# libgsasl 2.2.4 鸿蒙 PC 配方候选

## 版本、来源与范围

- 2.2.4 是 GNU SASL 的真实上游发行版。官方源码：`https://ftp.gnu.org/gnu/gsasl/gsasl-2.2.4.tar.gz`；SHA-256：`d32be15efd3a04cb19b232f721bdca02cc6ad7ab415df7d79fb2dd2c0da3e0be`。
- 本候选按看板依赖任务 `upgrade/libgsasl-2.2.4` 提供 LGPL-2.1-or-later C 静态库、3 个公开头文件及 `libgsasl.pc`。现有 `libgsasl-tools/2.2.4` 任务只交付 GPL 命令行工具，未交付库，因此不是同版库实现。
- 配方采用现有工具配方的 OHOS `config.guess` / `config.sub` 补丁，关闭本目标未提供的 GnuTLS、stringprep、GSSAPI、GS2 与 NTLM 集成。Conan 包不交付 GPL 命令行工具；许可证文件为 `COPYING.LESSER`。

## 目标验证

| 项目 | 结果 | 原始证据 |
| --- | --- | --- |
| 授权 OHOS/armv8 原生 Conan create | RC 0；`libgsasl.a`、`libgsasl.pc`、3 个头文件和许可证进入安装包 | 私有 a753 `create.log`，SHA-256 `5c4120d73aed15fcd09aba9f33d04ebe1f3cad0fde9a462ef49d385fae061a42` |
| `test_package` | 从安装包经 CMakeDeps 编译、链接并在目标运行；创建 PLAIN 会话并核对含 NUL 分隔符的完整认证消息 | 私有 a758 `create.log`，SHA-256 `a39f0599d8dd60bec2ab19a00daa24b66ed360812b5e478cf631f11dda931a58`；目标 Conan create RC 0 |
| 上游测试 | 选定 `version`、`simple`、`cram-md5`、`digest-md5`、`scram`、`scram-sha256`：6/6 PASS、0 SKIP、0 FAIL | 私有 a757 `upstream-a757.log`，SHA-256 `aa56303dd175751aff3fe4ef4f318a5e4ff4b173a96a26a10ffe4cad5aeabf5c` |
| 完整上游测试诊断 | `TMPDIR` 指向隔离可写目录后，32 TOTAL、26 PASS、6 SKIP、0 FAIL、`make check` RC 0；跳过项未计作通过 | 私有 a761 `upstream-full-a761.log`，SHA-256 `13bf07db88eb77d8c90b79f31a3cc803217b9d2c32aaa13345beca92ce72c829` |
| pkg-config 消费者 | `--cflags`、`--libs` 分别返回安装包内 include/lib 路径和 `-lgsasl`，RC 0；包内无 `.la` | 私有 a756 `pkg-config-check.txt`，SHA-256 `e9e89865e6438d7e7123e31d14e2d40d05c5bba296c2a2c8198f8e1bae12f24c` |

完整上游测试套件已在私有 a758 构建树中运行：首轮 a760 因目标 `/tmp` 只读，`gsasl-scram-pbkdf2.sh` 使用 `mktemp` 失败，25 PASS、6 SKIP、1 FAIL；原始 `upstream-full-a760.log` SHA-256 `bdd06a1282517b55dcd9f3059cb6f3ff2d51c488494a131ea0d6e24a3a11745c`，该单项日志 SHA-256 `91225f728389101b85f90822b1763054a0afb0836b23d6963b8c176426fe50a4`。未改上游源码，仅在第二次运行设置 `TMPDIR` 为该隔离根下已存在的可写 `tmp/`，a761 复测 26 PASS、6 SKIP、0 FAIL。六个 SKIP 是上游套件在当前禁用可选集成及目标环境下跳过，不写作 PASS。以上均为隔离私有目标验证，不代表官方 W3、平台 CI、审核、合入或积分。正式 W3 需等待框架回执流程与当前官方 main 绑定后执行，不手工制作 `.ci-result.json`。

a758 仅强化消费者测试，配方及上游补丁与 a753 逐字节相同。新的测试从安装包调用 `gsasl_client_start`、设置身份和口令、调用 `gsasl_step`，将生成的二进制 PLAIN 响应与 `\0jas\0secret` 逐字节比较，并释放会话及输出。授权目标新鲜传输和独立回读均通过；`target-native-a758/evidence.json` 记录输入哈希、目标原始日志哈希和 RC 0。该安装包消费者测试覆盖消息生成，不声称服务器认证；完整上游套件的单独结果见上表 a761。

隔离 a759 使用授权设备现有 PyYAML 6.0.3 解析候选 `manifest.yaml` 与 `conandata.yml`，两文件传输和回读逐字节一致；`software/version/build_system/status`、源 URL 与 SHA-256、两条补丁引用均通过检查。原始 `target-yaml-a759.txt` SHA-256 `5ff3d1b9a3f9c3f2d6952f89635ff69ee1220ab9f1eab36876677e931fba9003`。这只是 YAML 语法与所列字段的私有检查，不是官方 L0、正式 W3 或平台 CI。

将候选七个实施文件与 a758 的逐字节目标回执逐项比较后，在同一隔离配方上运行目标 Conan 2 `conan inspect --format=json`，RC 0。输出确认 `libgsasl/2.2.4`、`LGPL-2.1-or-later`、`static-library` 及四项设置；原始 `target-conan-inspect-a758.json` 1,761 字节，SHA-256 `6e68b2d65a69a98b6c3228faeb58c11bb8685d1d14397995c1ff24b41e7c8252`。这是私有元数据验证，不代替平台 L0/W3。

## 配方修复

上游 `libgsasl.pc` 在 Conan 的 `--prefix=/`、`DESTDIR=<package>` 安装下写成 `prefix=/`，会使直接使用 pkg-config 的下游指向设备根目录。安装后改为 `prefix=${pcfiledir}/../..`，并移除携带构建时路径的 libtool `.la`。这是下游配方修复，不宣称上游发布了新版本。

## 提交范围

仅提交本目录内的配方、官方来源摘要、两个 OHOS 补丁、清单、说明和 `test_package` 源文件。源码归档、下载缓存、目标 profile、私有日志与回执留在本地，不进入 PR。
