# unudhcpd 0.2.1-r2 — 编译适配记录

> 软件: unudhcpd 0.2.1-r2
> 平台: OpenHarmony / HarmonyOS PC, aarch64 (armv8)
> 适配路径: 路径 A（基础适配）
> 记录时间: 2026-10-13

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | unudhcpd |
| 上游版本 | 0.2.1（GitLab tag） |
| 包版本 | 0.2.1-r2（沿用平台心愿单指定版本） |
| 语言 | C |
| 构建系统 | Meson（`meson.build` + `tests/meson.build`） |
| 上游仓库 | https://gitlab.postmarketos.org/postMarketOS/unudhcpd |
| 许可证 | GPL-3.0-or-later |
| 包类型 | application（产物 `bin/unudhcpd`，非库） |
| 外部依赖 | 无（仅 libc：`inet_aton` / `getprotobyname` / `socket` / `ioctl`） |
| 补丁数 | **0**（上游源码零修改） |
| 归档目录 | `archives/u/unudhcpd/0.2.1-r2/` |

**源码 SHA256**（本机实测下载核验）：
`c404424a65e6341ef04300e7408a2edad1481ce8841f541e20e058800e7b5485`

## 二、编译阶段

### Phase 1: 环境与语言预检
- [x] 语言预检（R47）通过：`detected_language=c`（任务 cpp，c↔cpp 兼容族）
      - 构建系统证据：`meson.build` 中 `project('unudhcpd', 'c', ...)`
      - 源码统计证据：源文件 6 个（c:6），主体占比 100%
- [x] 源码官方源下载 + SHA256 核验

### Phase 2: 编译
- [x] Meson configure 通过（clang 15.0.4，原生 OHOS aarch64，非交叉编译）
- [x] Meson build 通过（**零补丁**）
- [x] Meson install 通过（`bin/unudhcpd`）

### Phase 3: 测试验证（层1 上游官方测试）
- [x] `meson test` 实测：`Ok: 3 / Fail: 0` → **3/3 套件（24 条断言用例）100%**

### Phase 4: 配方与消费者测试（层2 test_package）
- [x] `test_package/test.sh` 真实执行已安装二进制，**3/3 checks PASS**

### Phase 5: 归档收尾
- [x] `conan create` 全流程通过（含上游测试 + test_package）
- [x] `conan-verify` 通过（G0-G4 / L2 / L4 / L5）
- [x] W3 本地 CI 模拟通过（L0/L1/L4/L5 pass，L1e 破坏性反向验证 pass）
- [x] W4 Pre-PR 独立审计通过（P0=0 / P1=0，2 项 P3 非阻断）
- [x] 软件级 `commands.json`（R38）与两级 `manifest.yaml`、`README.md` 齐备

## 三、关键决策与踩坑记录

### 1. 历史归档为不可用模板残件，已整体重写
`archives/u/unudhcpd/0.2.1-r2/` 原有内容由批量导入生成（提交 `dac6280f3c`
"add 32 software packages CI input files"），存在四处硬伤：

| 问题 | 违规 | 处理 |
|------|------|------|
| `conandata.yml` 的 `sha256` 为空 | L0g 门禁必挂 | 实测补齐真实 SHA256 |
| 源码 URL 指向个人 fork `github.com/99degree/unudhcpd` | **R39** | 换为上游官方 GitLab 源 |
| `cpp_info.libs = ["unudhcpd"]` 把可执行文件当库 | 配方错误 | 改为 `package_type="application"` + `bindirs` |
| `test_package/test.c` 仅打印字符串 | **R34**（空壳测试） | 删除，改为真实执行二进制的 `test.sh` |

### 2. Conan 2 Meson 助手 API 漂移（真实报错 → 修复）
首次 `conan create` 报错：

```
ERROR: unudhcpd/0.2.1-r2: Error in build() method, line 53
	meson.compile()
	AttributeError: 'Meson' object has no attribute 'compile'
```

**根因**：Conan 2.29.1 的 `Meson` 助手公开方法为 `configure/build/install/test`，
而 `docs/ADAPTATION_GUIDE.md §4.4` 的 Meson 模板仍写 `meson.compile()`（Conan 1.x 旧写法）。

**修复**：改用 `meson.build()`。

**影响面**：该模板是 Meson 类新配方的公共起点，后续 Meson 配方会重复踩同一坑。
建议单独提 PR 修订模板（属框架文件，按 W2 须独立 PR）。

### 3. 上游版本号自身不一致（上游遗留，未修改）
上游 `meson.build` 写 `project(version: '0.1')`，与发布 tag `0.2.1` 不符，
因此 `unudhcpd -v` 实测输出 **`unudhcpd 0.1`**。为保持上游行为**未修改源码**，
已在 README 与 manifest 中如实披露。`test_package` 的断言以 `^unudhcpd ` 前缀匹配，
不硬编码错误版本号。

### 4. 运行期权限限制
服务绑定网卡走 `SO_BINDTODEVICE`，需 `CAP_NET_RAW`（通常需 root）。
故 `test_package` 只验证启动路径与参数解析，不做真实收包。

### 5. 临时文件规范（R10）
`test.sh` 的日志输出到 `${TMPDIR:-$HOME/tmp}`（OHOS `/tmp` 只读），
不写入 recipe 目录，结束时清理，避免污染仓库。

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| （无） | 上游源码在 OHOS aarch64 直接编译通过 | — | 零补丁 |

`patches/` 为空，`conandata.yml` 的 `patches: {}`。

## 五、测试记录（真机实测）

| 层级 | 命令 | 结果 |
|------|------|------|
| 层1 上游官方测试 | `meson test` | `Ok: 3 / Fail: 0`（`Test mac_to_str` / `Test dhcp_is_invalid_request` / `Test dhcp_get_request_type`，合计 24 条断言用例） |
| 层2 test_package | `conan test test_package unudhcpd/0.2.1-r2` | 3/3 checks PASS |

`test_package/test.sh` 三项检查的实测输出：

```
PASS 1: -v -> unudhcpd 0.1
PASS 2: no-arg -> usage, rc=1
PASS 3: server start path: Trying to start server with parameters:
        Server IP addr: 10.9.8.1:16767, client IP addr: 10.9.8.2, interface: lo
```

CI 模拟（`ci/conan/build_and_test.sh`，prdiff 模式）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L1e: Negative test confirmed — test genuinely depends on unudhcpd
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Total: 1 / Success: 1 / Pass rate: 100.0%
```

> 注：L2 smoke test 以 `--version` 探测失败（本工具仅实现 `-v`），门禁标记为 skip，非阻塞。

## 六、结束记录

- **最终状态**: built
- 验证结论：`conan create` + `conan-verify` + W3 本地 CI 模拟 + W4 独立审计 全部通过
- 未发布（未 `conan upload`），故状态为 `built` 而非 `published`（R29）
- 结束时间: 2026-10-13
---

**编译结束**: 2026-10-13 00:22
**最终状态**: built
