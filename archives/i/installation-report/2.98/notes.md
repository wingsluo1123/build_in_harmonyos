# installation-report 2.98 适配笔记

## 打包环境
- **类型**: Debian **native 脚本包**（无编译产物）：`report-hw`、`httpd`、`usb-list` 三个可执行脚本 + 安装器钩子（`pre-pkgsel.d/50save-logs`、`finish-install.d/94save-logs`）+ debconf 模板数据 + bug 报告脚本 + man 页 + 文档
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: **无 Conan requires**（详情见下）
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/i/installation-report/2.98 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码（source()）
Debian native 包（无独立上游仓库），**2.98 在 pool 里仍可直取**（不同于被较新修订覆盖的 init-system-helpers 1.69）：
`https://deb.debian.org/debian/pool/main/i/installation-report/installation-report_2.98.tar.xz`
（sha256 `119b1c56…`），`strip_root=True`。

### 2. 不跑 dh（关键适配点）
`debian/rules` 全文只有 `%: dh $@`，OHOS 无 dh/debhelper → 按 `debian/*.install`
（`installation-report.install`、`save-logs.install`）、`debian/*.manpages`、`debian/*.links`
声明的映射**直接安装**（与同族 `archives/i/init-system-helpers/1.69` 同一做法）：

| 源内路径 | 包内落点 | 依据 |
|---|---|---|
| `report-hw` | `bin/report-hw` | installation-report.install |
| `httpd`、`usb-list` | `bin/` | save-logs.install（「report-hw httpd usb-list usr/bin」） |
| `install-report.template` | `share/installation-report/` **与** `share/save-logs/` | 两个 install 清单各引用一次 |
| `bug/`（installation-report/{control,script}、installation-reports/script） | `share/bug/` | installation-report.install（「bug usr/share」） |
| `pre-pkgsel.d/`、`finish-install.d/` | `lib/pre-pkgsel.d/`、`lib/finish-install.d/` | save-logs.install |
| `report-hw.1` | `share/man/man1/` | installation-report.manpages |
| `debian/…README.Debian` | `share/doc/installation-report/` | dh_installdocs 默认行为 |
| `share/doc/installation-report/install-report.template` | **软链** → `../../installation-report/install-report.template` | installation-report.links |

### 3. 依赖为什么是"零"
`debian/control` 的 **Build-Depends 仅 `debhelper-compat (= 13)`、Depends 仅 `${misc:Depends}`**；
脚本运行时只用 `/bin/sh`。脚本里确实出现 `lspci`/`lsusb`/`dmidecode`，但：
- `report-hw` 注释明确写着「behaving robustly if commands are missing or broken」，
- 调用点都有存在性守卫/降级路径（`addfile`/`addinfo` 等封装的 `if [ -r ... ]`/命令探测），

→ 它们是**可选调用**，不构成打包依赖（判据是脚本注释与守卫写法，而不是 grep 到命令名）。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 测试文件 | **无**：包内无 `Makefile`、无 `t/`、无 `debian/tests`；`debian/rules` 全文仅 `%: dh $@` |
| 结论 | **上游确无测试** → 上游通过率记 **N/A**（如实披露，不虚构） |
| 构建期证据 | `build()` 对 5 个脚本做 `sh -n` 语法检查（任一不过即让 build 失败） |
| 消费者验证 | `test_package/test_scripts.sh` 5 项（脚本齐备/可执行、shebang、语法、数据产物与软链、best-effort 真跑） |

## 实测结果（本地 conan create，2026-10-08）

```
installation-report/2.98: [build] shell 语法检查通过：5 个脚本（上游无测试，通过率 N/A）
installation-report/2.98: Package '…' created
[ok]   5 个脚本齐备、非空、可执行（bin/×3 + lib/×2）
[ok]   5 个脚本 shebang 均为 /bin/sh
[ok]   sh -n 语法检查全部通过
[ok]   数据产物齐备（模板/文档/man/bug 脚本 + 软链可解析）
[skip] 具名环境信号：宿主无 USB 设备（/sys/bus/usb/devices 为空，条目数 0）→ usb-list 在 set -e 下按设计返回非 0
[skip] httpd 默认绑特权端口 :80，按设计不在此校验中运行（非缺陷）
[ok]   best-effort 真跑：1 个脚本在本环境成功执行
checks=5 fails=0 skips=2
RESULT: PASS
```

- 上游通过率：**N/A**（上游无测试，清点证据见下节）
- 消费者校验：**5 项中 3 通过 + 2 项具名环境 SKIP**

### 过程中踩到的两个坑（都可复用）

1. **conandata 里的 sha256 字符串混进不可见字符 → Conan 报"哈希相同却校验失败"**
   （长度 67 而非 64，终端里两串看起来一模一样）：
   ```
   ConanException: sha256 hash failed for '119b1c56…de40' file.
    Provided hash: 119b1c56…de40      ← 与下面视觉相同
    Computed hash: 119b1c56…de40
   ```
   判别与处置：用脚本量长度/字符集而非肉眼看（`len(hash)==64` 且 `[0-9a-f]{64}`），
   把哈希值改成"由文件实算得到"的字符串（本次用 `hashlib.sha256(文件).hexdigest()` 直接写入并立即回校）。
2. **upstream 脚本带 `set -e` 时，宿主缺少其"前置条件"会按设计返回非 0**：
   `usb-list` 遍历 `/sys/bus/usb/devices/usb*`，本沙箱该目录**为空**（无 USB 设备）→ 内部
   `[ -d '…usb*' ]` 为假 → `return` 非 0 → 受 `set -e` 影响脚本以 1 退出。
   这不是打包缺陷：消费者校验改为**先探测前置条件**（条目数为 0 → 具名环境 SKIP 并打印依据），
   有设备时仍按"具名信号才 SKIP、其余判缺陷"的口径严格校验。

## 复用来源

- Debian native 脚本包范式（不跑 dh、照抄 install/manpages/links 映射）沿用本会话已合入的
  `archives/i/init-system-helpers/1.69`；
- 消费者校验的"**仅具名环境信号可 SKIP**、其余判缺陷"口径沿用 PR #14983 的 aireview 修正。
