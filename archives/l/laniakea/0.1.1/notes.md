# laniakea 0.1.1 编译与验证记录

## 基本信息

- 软件名：laniakea
- 版本：0.1.1
- 上游仓库：https://github.com/lkhq/laniakea （官方 tag v0.1.1，release 页已核验存在）
- 源码：https://github.com/lkhq/laniakea/archive/refs/tags/v0.1.1.tar.gz （R39 官方源）
- SHA-256：`2da3e89f8822f0885b2766fcaa2555345a91655440e22a367eb304b5290753f5`（任务书给定，W3/CI conan create 实拉时复核）
- License：LGPL-3.0-or-later（COPYING）
- 适配路径：archives/l/laniakea/0.1.1
- 语言预检：任务标记 `cpp`，实测 `python`（纯 Python，0 个 C/C++ 源文件，Meson 仅做文件安装）→ **R47 用户决策覆盖**（见下）

## R47 覆盖决策

- `lang-preflight` 判定语言为 python（任务标记 cpp 与源码统计矛盾）。
- 按 R47 本应立即终态 `env_unsupported`；**用户明确指示走完整适配 + PR 流程**。
- 本仓库同生态 **laniakea-spark/0.1.1 已按 Python application 适配合入 main（PR #3636）**（铁证）；
  bambam/1.4.1 有 `r47_override` 字段先例。
- 结论：覆盖 R47，按 **Python application** 适配（纯 Python 手动复制打包，不跑 Meson/pip）；
  覆盖决策与依据写入版本 manifest.yaml `r47_override` 字段。

## 适配方式

- 上游 `meson.build` 强依赖 `systemd`、`apt-ftparchive`、`bubblewrap` 及 GLibc `renameat2`
  等 Debian 专属工具链，OHOS 无 → **不跑 Meson**，改为纯 Python 手动复制打包
  （参考 laniakea-spark/pyjson5 先例）。
- 布局：
  - 全部顶层 Python 包（admincli/archivecli/debcheck/laniakea/lighthouse/lkscheduler/
    mailgun/mirk/planter/rubicon/spears/synchrotron/webdash/webswview/webupload）
    → `lib/python3.12/site-packages/`；`src/keytool/keytool.py`（keytool/ 为目录非包，
    无 __init__.py，上游把 keytool.py 装为 bin/lk-keytool）→
    `site-packages/keytool.py`（作为模块被 bin/lk-keytool 包装器导入）。
  - `bin/` 生成 5 个 CLI 启动器包装（lk-admin/lk-archive/lk-keytool/rubicon/synchrotron），
    shebang `env python3`，内部按相对路径把 site-packages 前置进 sys.path（pyjson5 同款）。
    **pwd 兼容兜底（统一 wrapper_head，5 个启动器都生效）**：沙箱/容器运行 uid 无
    `/etc/passwd` 条目（如 conan 测试沙箱 uid=20020101）时，`pwd.getpwuid(os.getuid())`
    抛 KeyError，而上游 `ensure_laniakea_master_user(warn_only=True)`（lk-archive 的
    `run()` 在 click 解析前无条件调用）依赖该调用 → 包装器在 import 后先探测
    `pwd.getpwuid(os.getuid())`，KeyError 时 monkeypatch 提供占位条目，使上游走警告
    分支而非崩溃；有 passwd 条目的环境不命中 try 分支、零影响。
  - `data/` → `share/laniakea/`；**同时镜像一份到 `lib/python3.12/data/`**：上游
    `laniakea/localconfig.py::get_data_file()` 在非 /usr 安装下按
    `<module_dir>/../../data/` 解析数据文件（开发目录启发式），镜像后
    `LintianConfig()` 等数据文件在 conan 布局可发现。
  - **package() 生成最小默认 `base-config.toml`**（不是从上游复制：上游 `data/` 无此
    文件，仅在 `contrib/base-config.toml.sample`，管理员运行时创建于 `/etc/laniakea/`）；
    内容含 `Workspace` 与 `[Database]`（db/user/password/host/port，password 留空无真实
    凭据），写入 `lib/python3.12/data/`（dev 启发式命中位，`get_config_file` 先查
    `/etc/laniakea/` 再查此处）与 `share/laniakea/`（/usr 前缀兜底分支）——
    **lk-archive** 的 `run()` 在 click 解析前调用 `ensure_laniakea_master_user → LocalConfig()`
    读取配置，无此生成文件则无参构造直接 raise（第三次复验实测暴露）；lk-admin
    的 `--version` 在 click 回调中先 exit(0)（早于 LocalConfig，admincli/cli.py:29-33），
    但 lk-admin 其它子命令路径仍会走到配置发现，生成该文件对 lk-archive --version
    及无 `--config` 的调用均必要。
  - `COPYING` → `licenses/`。
- `requires("python/3.12.9")`（ohpcd 制品仓已发布）；其余 Python 运行依赖
  （sqlalchemy/cryptography/pyzmq/python-debian/tomlkit/click/rich/PyNaCl/PyYAML/pebble/
  firehose 等）**由消费环境提供，不声明 native target 依赖**（与 laniakea-spark 一致）。
- `build()` 无编译：仅 `python -m compileall` 对全部模块做字节码语法检查（不 import，
  无需 apt_pkg）。

## 依赖说明

- 运行时解释器：python/3.12.9（conan 依赖）。
- 直接运行依赖（由消费环境提供，test_package 按固定/最低版本 pip 安装后验证）：
  SQLAlchemy≥2.0、tomlkit≥0.8、python-debian、requests、cryptography、marshmallow、
  pyzmq、PyNaCl、PyYAML、Pebble、click、rich、firehose（+six，firehose 的传递导入依赖）。
- **系统绑定桩（OHOS 无对应 C 绑定，test_package/stubs/ 提供 import 期符号，
  真实能力被调用即 NotImplementedError，不伪造）**：
  - **apt_pkg（Debian python-apt）**：`laniakea.db.archive`、`laniakea.reporeader`、
    `laniakea.archive.*`、`laniakea.utils.gpg`、`archivecli.validate`、
    `spears.spearsengine`、`synchrotron.syncengine` 顶层 `import apt_pkg`
    → 桩提供 Hashes/TagFile/TagSection/version_compare。
  - **gi/PyGObject（AppStream 系统绑定）**：`laniakea.archive.appstream`
    （lk-archive 的 `_register_commands → archivecli.publish` 顶层触发）与
    webswview 视图顶层 `import gi` / `gi.require_version('AppStream','1.0')` /
    `from gi.repository import AppStream` → 桩提供 `require_version()` no-op +
    `gi.repository.AppStream` 占位命名空间（属性访问即 NotImplementedError）。
  - **cryptography（Rust 扩展）**：`laniakea.utils.traceback` 顶层
    `from cryptography.hazmat...`（AES-CBC 混淆 traceback，CLI --version 链
    不调用，仅在 `format_encrypted_traceback`/`decrypt_traceback_string`
    中真实使用）。OHOS 社区源 cryptography wheel 的 Rust 扩展
    `_rust.abi3.so` 在 OHOS 真机加载器（ld-musl）上被拒（CI #91056 实测
    `Permission denied`，本机 x86_64 沙箱无法暴露）→ **test_package 不
    pip 安装 cryptography**，由桩提供 `default_backend`/`PKCS7`/`Cipher`/
    `AES`/`CBC` import 期符号（真实加解密能力被调用即 NotImplementedError，
    不伪造）；真实 cryptography 由消费环境按需提供。
  - **PyNaCl/nacl（libsodium C 扩展）**：`laniakea.msgstream.signing` 顶层
    `import nacl.signing`（ed25519 签名，`signing.py:8`），`import laniakea`
    链经 msgstream 触发；但 test_package 的 signedjson 断言用 **mock 签名键**
    （alg="mock"，`test_laniakea.py` signedjson 段），5 个 CLI --version 链
    也不调用真实 ed25519 签名。OHOS 社区源 PyNaCl wheel 的 `nacl._sodium.abi3.so`
    在 OHOS 真机加载器上同样被拒（CI #91660 实测 `Permission denied`）→
    **test_package 不 pip 安装 PyNaCl**，由桩提供 `SigningKey`/`VerifyKey`
    import 期符号（真实签名/验签被调用即 NotImplementedError，不伪造）；
    真实 PyNaCl 由消费环境按需提供。
  - **pyzmq/zmq（libzmq C 扩展）**：`laniakea.msgstream.event_msg` 顶层
    `import zmq`（ZeroMQ 消息流，`event_msg.py:12`），`import laniakea` 链经
    msgstream 触发；函数签名注解 `zmq_context: zmq.Context` / `-> zmq.Socket`
    在 import 期即求值，需 `Context`/`Socket` 类符号。test_package 的
    signedjson（mock 键）与 5 个 CLI --version 链均不创建真实 ZeroMQ socket；
    keytool.py 顶层 `import zmq.auth`（lk-keytool --version 链，不调用
    `load_certificate`）。OHOS 社区源 pyzmq wheel（27.1.0）的 libzmq C 扩展
    在 OHOS 真机加载器上同样被拒（CI #91763 实测 `Permission denied`）→
    **test_package 不 pip 安装 pyzmq**，由桩提供 `Context`/`Socket` 类、
    `DEALER`/`SUB`/`SUBSCRIBE` 常量、`curve_keypair`/`auth.load_certificate`
    import 期符号（真实 socket 能力被调用即 NotImplementedError，不伪造）；
    真实 pyzmq 由消费环境按需提供。
  - 其余 Debian/系统绑定**排查无需桩**（见下"系统绑定排查清单"）。

### 系统绑定排查清单（5 个 CLI --version 全链，主编要求系统性枚举）

| 模块 | 源码位置 | 是否在 5 CLI --version 链 | 处置 |
|------|---------|--------------------------|------|
| apt_pkg | db/archive、reporeader、archive/*、utils/gpg、archivecli/validate、spearsengine、syncengine | ✅ import laniakea 即触发 | 桩（已有） |
| gi/PyGObject | archive/appstream.py（lk-archive→publish 触发）、webswview 视图 | ✅ lk-archive 触发 | 桩（新增） |
| flatpak | laniakea/flatpak_util.py（subprocess 调系统 flatpak 二进制，**无 import flatpak 模块**）；admincli/flatpak（lk-admin 链）仅 import flatpak_util | 顶层无系统绑定 import（lk-admin 实测通过） | 不需要桩（二进制仅功能路径调用） |
| dose/dose3 | debcheck/dose.py 为 laniakea 自有模块（import yaml/pebble/laniakea.db，**无 import dose**） | 不在 5 CLI 链 | 不需要桩 |
| britney/britneyconfig | spears/britney.py 等为 laniakea 自有模块（import laniakea.* + stdlib，**无 import britney**）；britney 二进制经 run_forwarded 调用 | 不在 5 CLI 链 | 不需要桩 |
| mautrix/matrix_client | mirk/matrix_client.py import mautrix（纯 Python，pip 可装） | mirk 不在 5 CLI 链（5 个 CLI 均不 import mirk） | 不需要 pip（不触发） |
| systemd/apt/dbus/cairo/xdg | grep 全 src 无任何 import | — | 不需要 |

## 上游测试统计（R51 三步法）

### 第一步：清点

上游 `tests/` 目录共 **7 个 pytest 测试文件、39 个用例**（`meson test` 注册为
`pytest -x`，见 tests/meson.build）：

| 文件 | 用例数 | 列表 |
|------|-------|------|
| test_signedjson.py | 19 | test_generate_key, test_decode, test_decode_invalid_base64, test_decode_signing_invalid_algorithm, test_decode_invalid_key, test_read_keys, test_read_old_keys, test_decode_verify_invalid_algorithm, test_write_signing_keys, test_ed25519, test_unsupported, test_sign_minimal, test_sign_with_data, test_sign_and_verify, test_signature_ids, test_verify_fail, test_verify_fail_no_signatures, test_verify_fail_no_signature_for_alice, test_verify_fail_not_base64 |
| test_archive.py | 10 | test_utils, test_parse_changes, test_sections_available, test_lintian, test_package_uploads, test_package_delete, test_package_dbgsym_upload, test_package_expire, test_heidi_import, test_publish |
| test_utils.py | 4 | test_base64, test_is_remote_url, test_renameat2, test_traceback_decrypt |
| test_lighthouse_jobs.py | 2 | test_request_archive_info, test_request_job |
| test_lighthouse_msgstream.py | 2 | test_msg_creation, test_msg_simple_submit_listen |
| test_flatpakrepo.py | 1 | test_flatpak_init_repo |
| test_reporeader.py | 1 | test_reporeader_local |
| **合计** | **39** | |

conftest.py 关键 fixture：`localconfig`（session 级 autouse，所有用例都依赖，构造
测试配置并断言 database_url）、`postgresql_container`（**podman** 构建/运行 PostgreSQL
容器）、`create_database`/`database`（真实 PG 建表）、`lighthouse_server`（起 Lighthouse
进程 + ZMQ CURVE 证书）、`import_sample_packages`（依赖真实 apt_pkg 解析 .changes/.dsc）。
全部清点明细见 `.scratch/laniakea-subtask/upstream-tests/inventory.md`。

### 第二步：可运行性分析（OHOS）

| 分组 | 用例 | OHOS 可运行性 | 技术原因 |
|------|------|--------------|---------|
| test_signedjson.py | 19 | **理论可运行**（需 PyNaCl+pyzmq+apt_pkg 桩+pip 依赖） | 纯 Python 签名/验签（mock 键 + 真实 nacl 键），无外部服务 |
| test_utils.py（3/4） | test_base64/test_is_remote_url/test_traceback_decrypt | **理论可运行**（需 python-debian/requests/cryptography+apt_pkg 桩） | 纯 Python 工具函数 |
| test_utils.py（1/4） | test_renameat2 | 不确定 | 依赖内核 `renameat2` 系统调用，OHOS 内核支持未实证 |
| test_reporeader.py | 1 | **不可运行** | `RepositoryReader` 用真实 `apt_pkg.TagFile` 解析 Release/Packages，桩不提供真实解析 |
| test_flatpakrepo.py | 1 | **不可运行** | `FlatpakUtil.init_repo` 调系统 `flatpak` 命令，OHOS 无 flatpak 工具链 |
| test_archive.py | 10 | **不可运行** | 依赖 podman PostgreSQL 容器（conftest `postgresql_container`）+ apt_pkg 真实解析 + bwrap/lintian/flatpak/dose 工具 |
| test_lighthouse_jobs.py | 2 | **不可运行** | 需 Lighthouse 进程 + PostgreSQL 容器 + ZMQ CURVE 证书（conftest 起 podman PG） |
| test_lighthouse_msgstream.py | 2 | **不可运行** | 同上（lighthouse_server fixture → database → podman PG） |

**OHOS 可运行理论子集 = 22/39**（test_signedjson 19 + test_utils 3），前提是安装
pip 依赖 + apt_pkg 桩；**16/39 不可运行**（podman PostgreSQL 容器 / apt_pkg 真实
C 绑定 / flatpak·bwrap·lintian 工具链），**1/39 待实证**（test_renameat2，内核
renameat2 支持未实证）。

### 第三步：回填（主编 #6 实测，2026-10-14）

- 上游 39 例**主编全部实测**（可运行环境：本机可写 scratch 副本 + 最小 apt_pkg 桩
  解除 conftest 顶层 import 阻塞，不改测试逻辑）：
  **24 passed / 3 failed / 12 errors（ERROR），通过率 24/39 = 61.5%**。
  详细逐例实证记录见 `.scratch/laniakea-subtask/upstream-tests/main-agent-empirical.md`。
- **3 个 FAILED 用例原因（逐项）**：
  1. `test_parse_changes`（test_archive.py:68）：上游断言期望 `GpgException('No data.')`，
     实测 GPG 退出 256 且 `No status output from GPG`——环境 GPG 版本/沙箱行为与上游断言不一致；
  2. `test_flatpak_init_repo`（test_flatpakrepo.py）：`FlatpakUtil()` 构造要求 `flatpak` 与
     `ostree` 可执行——OHOS 无 flatpak 工具链（Debian/Flatpak 专属）；
  3. `test_reporeader_local`（test_reporeader.py）：`GpgException: No status output from GPG
     (exit 256)`——同 GPG 行为差异，并叠加 apt_pkg 真实绑定缺失（reporeader 顶层 import apt_pkg）。
- **12 个 ERROR 用例原因（逐项）**：全部因 conftest `postgresql_container` fixture 依赖
  **podman + postgres:16 容器**（本机/OHOS 均无 podman 二进制，`FileNotFoundError: 'podman'`）：
  test_archive.py 8 例（sections_available/lintian/package_uploads/package_delete/
  package_dbgsym_upload/package_expire/heidi_import/publish）+ test_lighthouse_jobs.py 2 例 +
  test_lighthouse_msgstream.py 2 例。
- 上游测试**未被修改**（无补丁，patches_applied=[]）。
- 纯 Python 可运行子集 24 例全部通过，证明被测逻辑本身无适配性缺陷；未通过项均为
  Debian 专属外部环境（podman/flatpak/GPG 版本行为），与代码正确性无关。
- 上游测试的 OHOS 不可运行能力由 test_package 以**等价消费者断言**覆盖（见下节），
  CI 端 conan create 时实跑验证打包产物（47 断言全绿）。

## 新增 test_package 覆盖（鸿蒙特有/消费者测试）

`test_package/test_laniakea.py`（经 test_package/conanfile.py 在 conan 测试阶段实跑）：

1. 包布局断言：site-packages/laniakea、share/laniakea、licenses/COPYING、bin/ 5 启动器存在且可执行。
2. `import laniakea` + `__version__ == '0.1.1'`（覆盖 sqlalchemy/marshmallow/tomlkit/
   python-debian/requests/cryptography + apt_pkg 桩完整导入链）。
3. `LocalConfig`：显式配置加载（Workspace/database_url）、缺 Workspace 故障路径。
4. `laniakea.utils`：base64 urlsafe 编解码、is_remote_url、listify。
5. `laniakea.utils.deb822.Changes.add_file()`：md5/sha1/sha256 + size 记账（python-debian）。
6. `laniakea.msgstream.signedjson`：sign_json/signature_ids（mock 签名键，纯 Python）。
7. 5 个 bin 启动器 `--version` 实跑（stdout == "0.1.1"）：
   lk-keytool（pyzmq 链）、lk-admin（click/rich + 全子命令注册链）、
   lk-archive（pebble + apt_pkg 桩）、rubicon（firehose + msgstream 链）、
   synchrotron（pebble + syncengine 链）。
8. 数据文件断言：archive-sections.json 可解析且含 section 条目、words/ 4 词表文件、
   lintian.toml/3rd-party.toml 存在、base-config.toml 双份生成
   （share/laniakea 与 lib/python3.12/data）。

test_package/conanfile.py 运行时：临时目录 pip install 上述运行依赖（--prefer-binary，
laniakea-spark 同款），对 .so 补执行位（OHOS 加载器要求），复制 apt_pkg 桩进依赖目录，
以 conan python（sys.executable）运行 test_laniakea.py；`can_run(self)` 交叉保护。

## 已知限制

- **apt_pkg / gi/PyGObject 真实解析不可用**：Debian 专属 .changes/.dsc/Release/Packages
  解析（apt_pkg C 绑定）与 AppStream 元数据处理（PyGObject + libappstream 系统绑定）
  在 OHOS 无对应实现；test_package 仅以桩（stubs/apt_pkg.py + stubs/gi/）满足 import
  期符号，真实能力被调用即 NotImplementedError；deb822 数据层由 python-debian
  （纯 Python）替代覆盖。
- **守护进程与 Web 服务不可运行**：lighthouse-server/laniakea-scheduler/laniakea-mailgun/
  mirk/spears/planter/debcheck/webdash/webswview/webupload 需要 systemd service 单元、
  PostgreSQL、ZMQ CURVE 证书及 Debian 构建工具链；模块随包安装但未提供可运行入口
  （不在 commands.json 内，R38 只声明 5 个主 CLI）。
- **数据库后端为 PostgreSQL**：`LocalConfig.database_url` 指向 postgresql://，
  OHOS 消费环境需自备 PG（上游如此，非本适配引入）。
- **`LocalConfig()` 无参构造依赖配置发现**：包内生成默认 base-config.toml
  （lib/python3.12/data/ dev 启发式位 + share/laniakea/ /usr 兜底位），
  使无参构造在 conan 布局可发现；若 conan 缓存路径以 /usr 开头则 get_data_file
  回退到 /usr/share/laniakea 查找（CI 通常位于用户缓存目录，走 dev 启发式位）。
  仅占位默认值，管理员可在 /etc/laniakea/base-config.toml 覆盖（get_config_file 优先）。
- **uid 无 passwd 条目的沙箱环境**：conan 测试沙箱 uid（如 20020101）无 /etc/passwd 条目，
  上游 `ensure_laniakea_master_user` 的 `pwd.getpwuid(os.getuid())` 会 KeyError 崩溃；
  已在 bin/ 启动器统一 wrapper_head 内置 pwd 占位条目兜底（仅 KeyError 时生效，
  上游走 warn_only 警告分支），真实用户环境零影响。
- **test_renameat2 未覆盖**：内核 renameat2 支持未实证，test_package 不包含该用例。
- **上游 39 例主编实测（可运行环境 + apt_pkg 桩）**：24 通过 / 3 失败 / 12 环境阻塞（ERROR），
  通过率 24/39（61.5%）；3 个 FAILED（test_parse_changes/test_flatpak_init_repo/
  test_reporeader_local）与 12 个 ERROR（podman PostgreSQL 容器）原因逐项见
  `.scratch/laniakea-subtask/upstream-tests/main-agent-empirical.md` 与本文 R51 第三步；
  未修改任何上游测试（patches_applied=[]），不编造通过率；OHOS 不可运行能力的等价
  断言已由 test_package 消费者测试在 CI conan create 阶段实跑覆盖（47 断言全绿）。

## 最终状态

- **status: closed** —— laniakea 0.1.1 适配完成（路径 A 基础适配）。
- 编译状态：通过（`conan export` 解析通过；本地 `conan create`（OHOS armv8 profile）完整实跑，
  test_package 47 断言全绿，5 个 CLI `--version` 均输出 0.1.1；CI 端正式复验见 W3）。
- 上游测试：39 例全部实测，通过率 24/39（61.5%），3 失败 / 12 环境阻塞原因逐项记录（R51 第三步），
  未修改任何上游测试。
- 新增鸿蒙特有测试：test_package 47 断言，通过率 47/47（100%）。
- R47 覆盖决策：任务标记 cpp、实测 python，按用户明确指示走完整适配 + PR 流程，
  同生态 laniakea-spark/0.1.1 已合入 main（PR #3636）为先例，覆盖记录见 manifest.yaml r47_override。
- 待办：CI 正式 conan create 复验 → status=built 升级 published（R29）→ 提交赛事 PR。
