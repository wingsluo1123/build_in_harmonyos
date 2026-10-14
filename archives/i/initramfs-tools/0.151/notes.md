# initramfs-tools 0.151 适配笔记

## 打包环境
- **类型**: Debian **native 包**（initramfs 构建工具集）：1 个 C 程序 `unmkinitramfs` + shell 工具 `mkinitramfs` / `update-initramfs` / `lsinitramfs` + `hooks/`、`scripts/` 框架 + 配置与 man 页
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: **无 Conan requires**（详见下）；测试框架 shunit2 仅在 build 期取用
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/i/initramfs-tools/0.151 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码（source()）
Debian native 包，0.151 在 pool 里可直接取：
`https://deb.debian.org/debian/pool/main/i/initramfs-tools/initramfs-tools_0.151.tar.xz`（sha256 `41e59498…`），`strip_root=True`。

### 2. 不跑 dh（关键适配点）
`debian/rules` 是 dh 流程（`dh $@ --with bash-completion`），OHOS 无 dh → 按
`debian/initramfs-tools*.install` 的映射**直接安装**（与同族 `installation-report`、`init-system-helpers` 同做法）：

| 源内路径 | 包内落点 | 依据 |
|---|---|---|
| `unmkinitramfs`（本包 make 产物） | `bin/unmkinitramfs` | install 清单（`usr/bin`） |
| `lsinitramfs` | `bin/lsinitramfs` | 同上 |
| `update-initramfs` | `sbin/update-initramfs` | initramfs-tools.install（`usr/sbin`） |
| `**mkinitramfs（模板）**` | `sbin/mkinitramfs` | debian/rules 的 `override_dh_install`：**sed 替换 `@VERSION@` / `@BUSYBOX_PACKAGES@` 后再安装** |
| `conf/initramfs.conf`、`conf/update-initramfs.conf` | `etc/initramfs-tools/` | install 清单 |
| `conf/modules`、`hook-functions`、`init`、`hooks/`、`scripts/` | `share/initramfs-tools/` | core.install |
| `kernel/`（空目录） | `etc/kernel/` | initramfs-tools.install（`kernel → etc`） |
| `debian/script` | `share/bug/initramfs-tools/script` | initramfs-tools.install |
| `*.5`/`*.7`/`*.8` | `share/man/man{5,7,8}/` | dh_installman |
| `bash_completion.d/` | `share/bash-completion/completions/initramfs-tools/` | `--with bash-completion` |

> **易错点**：`mkinitramfs` 是**带占位符的模板**，原样打包会把 `@VERSION@`/`@BUSYBOX_PACKAGES@` 带进产物；
> 配方里照 Debian 做替换，并在消费者校验里**断言占位符已消失且含版本号**。

### 3. 依赖为什么是"零"
`debian/control` 的 Build-Depends = `debhelper-compat (= 13), bash-completion, shunit2 <!nocheck>`：

- `debhelper-compat` 只是 dh 版本声明（本适配不跑 dh）；
- `bash-completion` 仅用于把源码自带的 `bash_completion.d/` 装到系统目录 → 不是构建依赖；
- **`shunit2` 带 `<!nocheck>` 标记，是测试框架**（仓库与制品仓都没有）→ 按"缺环境就下"在
  `build()` 内从 Debian pool 取 tarball（**钉真实 sha256** `b2fed28b…`，`strip_root=True`）仅用于跑测试，**不进产物**；
- Depends 是 `initramfs-tools-core` 等同源子包 → 无外部运行期库依赖。

## 上游测试清点（R51：N = tests/ 目录数 + 测试注册数）

**N = 16**（此前误记为 6，并把另一部分错说成"shunit2 框架自带的 example"——已更正）：

| 项 | 数量 | 依据 |
|----|----|----|
| ① `tests/functions_test` 的 `test_*` 函数 | **6** | `grep -cE '^\s*test[A-Za-z0-9_]*\(\)' tests/functions_test` = 6（POSIX sh + **shunit2**，需把 shunit2 放到 PATH 上） |
| ② `debian/tests/control` 注册的 Debian autopkgtest 用例 | **10** | `Tests:` 共 10 条：copy-file、unmkinitramfs、qemu-klibc、qemu-busybox、qemu-ata-only、qemu-virtio-only、qemu-separate-usr、qemu-panic-shell、qemu-net、qemu-net-iscsi |
| **合计 N** | **16** | 即审核「上游实测 N=16」 |

| 项 | 值 |
|----|----|
| 覆盖内容 | ①`scripts/functions` 里的纯函数（如 `_generate_hosts_content` 生成的 `/etc/hosts` 片段）；②initramfs 镜像构建与 QEMU 引导集成 |
| 运行方式 | ①在 build() 内取 shunit2 后真跑 6/6，按 shunit2 输出（`Ran N tests` + `OK` / `FAILED`）判定；②需 Debian 测试床 |
| 结果口径 | 出现 `FAILED`/`not ok` → 判不成立；**未取得运行结果同样判不成立**（不把"没真跑"记成通过） |

### 为什么 ② 的 10 个跑不了（平台级系统性阻塞，非"缺依赖"）

- 8 个 `qemu-*` + `copy-file`：autopkgtest 声明 `Restrictions: needs-root, breaks-testbed`，
  `Depends` 含 `linux-image-generic`（**Linux 内核镜像**）+ `qemu-system-native` + `genext2fs`/
  `ipxe-qemu`/`klibc-utils` → 必须在可引导的 **Debian 测试床**里以 root 跑 QEMU。
  OHOS/HarmonyOS 是非 Linux 内核、无 `dpkg`/`apt`/`linux-image-*`；本机实测
  `command -v qemu-system-x86_64` = **MISSING** → 架构上不可能满足。
- `unmkinitramfs`（唯一不需要 root 的）：`Depends=bzip2, lz4, lzop, xz-utils, zstd`，脚本
  `set -eu` 且逐一遍历 `gzip/bzip2/lzma/xz/lzop/lz4/zstd` **全部 8 种压缩器** → 缺一即中止；
  本机实测 `zstd`、`lzop` 均 **MISSING**。

> 以上均为可复现证据，已同步进版本级 `manifest.yaml` 的 `blocked_cases` 与
> `test_package/MANIFEST.yml` 的 `upstream_not_run`；**未把未跑的用例记成通过**。

## 实测结果（本地 conan create，2026-10-08）

```
initramfs-tools/0.151: [build] make all 产出 unmkinitramfs 成功
initramfs-tools/0.151: [upstream tests] shunit2: Ran 6 tests（6 个 test_* 函数）
initramfs-tools/0.151:     Ran 6 tests.
initramfs-tools/0.151:     OK
[ok]   关键产物齐备（15 项：工具 + hooks/scripts 框架 + 配置 + man）
[ok]   bin/unmkinitramfs 为 64 位 AArch64 ELF（来自本包 make all）
[ok]   模板替换已生效：sbin/mkinitramfs 无占位符残留且含版本号 0.151
[ok]   shell 产物 sh -n 语法检查全部通过（5 个，shell=/system/bin/sh）
[ok]   unmkinitramfs 真跑成功（exit=2）：Usage: unmkinitramfs [-v|--verbose] INITRAMFS-FILE DIRECTORY
checks=4 fails=0 skips=0
RESULT: PASS
```

- **上游**：`tests/functions_test` 6 个用例 **Ran 6 tests / OK（0 失败）**——真跑
- **消费者**：4 项全部通过（含真跑 `unmkinitramfs`，打印 Usage）

### 消费者校验落地时踩到的 4 个坑（都可复用）

1. **shell 重定向会"吞"测试输出**：最初用 `bash -c "… > <log> 2>&1"` + 事后读日志，
   实测输出跑到 conan 控制台、日志文件为空 → 解析不到 `Ran` 而误判"未真跑"（假失败）。
   改为在配方里用 **`subprocess.run(..., stdout=PIPE)` 直接捕获**输出，最稳。
2. **shunit2 输出带 ANSI 颜色码**：实测 repr 为 `Ran \x1b[1;36m6\x1b[0m tests.`、`\x1b[1;32mOK\x1b[0m`
   → `Ran (\d+) tests?` 永远匹配不到。解析前必须 `re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw)`
   剥掉转义序列，并归一化空白（`" ".join(text.split())`）。
   > 与 conandata 的 sha256 那次同类：**"看起来一样"的值不要靠肉眼，要按字符级手段处理**。
3. **test_package 运行环境里 PATH 可能不含 `/bin`**：`subprocess.run(["sh", …])` 直接
   `FileNotFoundError: 'sh'` → 改为按候选绝对路径（`shutil.which("sh")` → `/bin/sh` →
   `/usr/bin/sh` → `/system/bin/sh`）挑一个存在的（本机命中 `/system/bin/sh`）。
4. **模板化脚本要断言替换生效**：`mkinitramfs` 带 `@VERSION@`/`@BUSYBOX_PACKAGES@` 占位符，
   原样打包会把占位符带进产物 → 配方做替换，消费者校验断言"无残留 + 含版本号"。

## 复用来源

- Debian native 包范式（不跑 dh + 照抄 install 映射）沿用本会话的
  `archives/i/installation-report/2.98` 与 `archives/i/init-system-helpers/1.69`；
- "测试框架按需自取、钉子 sha256、不进产物"的做法沿用 npm 的 tape 与 perl 的 Test::Deep 先例；
- 消费者校验的"仅具名环境信号可 SKIP"口径沿用 PR #14983/#15010 的修正。
