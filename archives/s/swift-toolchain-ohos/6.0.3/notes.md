# notes.md — swift-toolchain-ohos 6.0.3（★ 预备件）

## 1. ★ PENDING-P2 占位清单（★ **四处**；答复到位前不得落地）

| # | 占位 | 现在的写法 | 受影响位置 | 答复来源 |
|---|---|---|---|---|
| **PENDING-P2-1** | **载荷托管 URL** | `<PENDING-P2:hosting>` | `conandata.yml` → `sources.url` | P2 §1-1（PF7 官方托管例外）＋ §1-2（能否随仓提交） |
| **PENDING-P2-2** | **版本号形态** | `6.0.3` | `conanfile.py` 的 `version`、`commands.json` 的 `versions` 键、版本目录名、`manifest.yaml` 的 `versions` 键 | P3 裁定（`6.0.3` vs `6.3.3`） |
| **PENDING-P2-3** | **`.swift` 测试源准入** | 用 `.sh` 外壳包着真 `swiftc` 编译 | `test_package/test_swift_toolchain.sh`、`test_package/MANIFEST.yml` | P2 §1-5／§1-6（白名单与语言准入流程） |
| **PENDING-P2-4** | ★★ **`conanfile.py` 的 `url` 字段该写什么** | `https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/s/swift-toolchain-ohos/6.0.3` | `conanfile.py` 的 `url`、软件级 `README.md` | **本轮新发现**，见 §1.1 |

★ **红线**：`conandata.yml` 里**不得**出现假 URL、**不得**出现 `file://` 或绝对路径
（那会踩 PF7 的另两条）；sha256 是**真值**，不许占位。

### 1.1 ★★ PENDING-P2-4 是怎么冒出来的（本轮 `prep_checks.py` 现场咬到的）

`prep_checks.py --all` 第一次跑就把这一条**判红**了：

```
!! PF7.blacklist-url-scan   expect=0  got=1
   conanfile.py:42 镜像前缀 cnb.cool（CI 自动加镜像回退，手写即 R39 违规 579 例）
```

查证后**这不是骨架写坏了，是门禁的作用域问题**，事实链如下：

1. **PF7 只扫 `conandata.yml` 与 `manifest.yaml`**：
   `scripts/ohc/preflight.py:385-397` 的 `check_source_urls` 逐个文件判
   `f.startswith("archives/")` **且** `f.endswith(("conandata.yml", "manifest.yaml"))`
   ⇒ **`conanfile.py` 的 `url = ` 字段完全不在 PF7 作用域内**。
2. **但 `cnb.cool` 确实在 PF7 的镜像黑名单里**：
   `preflight.py:356-360` 的 `_PF7_MIRROR_HOSTS` 含 `"cnb.cool"`。
3. **先例也是这么写的**：
   `archives/r/rust-toolchain/1.97.1/conanfile.py:31` 的 `url` 同样指向
   `https://cnb.cool/ohpcd/ohos-pc-archives/...` 的仓内路径。
   ⇒ 本骨架**与先例同形**，不是新引入的偏差。
4. **修正后的判据**：本骨架把这一项拆成**两条分开的记录**：
   * `PF7.blacklist-url-scan`（**上游口径**）⇒ `0`：`conandata.yml` 的 URL 是占位符，
     占位符本身不在黑名单内，但**也不能**算通过"官方源"要求 ⇒ 由 PENDING-P2-1 承接；
   * `PF7.conanfile-url-by-upstream-rule` ⇒ `out-of-scope`（**记录事实**，不冒充通过）；
   * 另加一行**不参与判绿**的 `LOCAL-STRICTER` 提示，写出"本机更严的读法会标记它"。

★ **为什么值得单列一条待裁项**：`cnb.cool` **看起来是组织自有的制品域名，却在黑名单内**
（P2 §1-1 已经问过这一点）。若验收方答复"`cnb.cool` 不可用"，
则**先例 `rust-toolchain` 的 `url` 字段与全仓同类字段都要一起改**；
若答复"可用"，则本骨架照抄先例即可。**两种答复下本骨架的改动量都是 1 行。**


## 2. 门禁对应表（写配方时逐条对上的框架条文）

| 门禁 | 条文位置 | 本骨架如何满足 |
|---|---|---|
| **G1** 八字面量 | `scripts/ohc/conan_verify.py:484-493` | `conanfile.py` 显式含 `name = ` / `version = ` / `def source(` / `def build(` / `def package(` / `def package_info(` / `export_sources` / `apply_conandata_patches` |
| **G1** conandata | 同上 `:505-521` | `sources:` ＋ `url:` 齐；无 `REPLACE_WITH` |
| **G1** 结构 | 同上 `:523-539` | `test_package/conanfile.py` ＋ `test_package/MANIFEST.yml` 齐 |
| **L0o** 禁外部下载命令 | `ci/conan/build_and_test.sh:904-915` | `source()` 只用 `conan.tools.files.get`；全文不出现那两个字面量 |
| **L0p** settings 四项 | 同上 `:917-931` | `settings = "os", "compiler", "build_type", "arch"` |
| **L0c/L0d/L0e** | 同上 `:345-378` | `.sh` 测试源 ＋ `test()` 内 `self.run` ＋ `MANIFEST.yml` |
| **L0k / R38** | 同上 `:684-765`；`preflight.py:475-554` | 软件级 `commands.json`：`type="tool"`、`name` 一致、`versions["6.0.3"].ref == "swift-toolchain-ohos/6.0.3"`、`binary:false` |
| **PF2** 制品闸 | `preflight.py:106-112` | 本骨架里**没有** tarball；载荷靠 URL 取（这正是 PENDING-P2-1 的问题） |
| **PF3** 测试实质 | `preflight.py:136-173` / `:434-456` | `test()` 调 `self.run`；测试源白名单内 |
| **PF5** 平台宏闸 | `preflight.py:245-272` | 补丁面**恰 2 条**（0001 包内前门 `swiftc.sh` 的 flag 表；0002 载荷绝对路径相对化，见 `patches/README.md`）⇒ **落地轮真被扫到**；两条改的都是 shell 文本与 module map 文本，不含平台宏 `#if defined(__OHOS__)` |
| **PF6** 共享前缀闸 | `preflight.py:275-311` | 全文无 `SYS_PREFIX` / 引号包裹的 `/usr/local` |
| **PF7** 源 URL 闸 | `preflight.py:356-426` | ★ **待答复**：URL 是占位；占位符本身不在黑名单内，但**也不能通过"官方源"要求** |
| **PF8** 配方静态闸 | `preflight.py:475-554` | settings 四项；版本目录名 == `version`；slug `[a-z0-9._+-]` 合规 |
| **PF9** 分支/路径闸 | `preflight.py:559-595` | 闸要求每条**变更**路径 ≥5 段；**软件级三件（`manifest.yaml`／`commands.json`／`README.md`）只有 4 段** ⇒ 落地轮实测口径（见落地轮任务书 v2 第 6 步） |
| **R32** | 同族先例 | `validate()` 用 `os not in ("Linux","OHOS")` 报错 |
| **R26** 系统同名库 | G3 `conan_verify.py:636-715` | 本包**不产出**与系统同名的 `.so`（ring 的 `libxml2.so.16` 带 `.16` 后缀，不是裸 `libxml2.so`）；无需静态链接配置 |
| **L5a/L5b/L5c** | `build_and_test.sh:1544-1593` | 对最小集 `lib/` 一级做 SONAME 三闸（见 `prep_checks.py` 的 L5a/L5b 项） |
| **408 MB** 单文件 | `archives/c/clang/22.1.8/notes.md:16-17` | 189,124,959 B ⇒ 余量 53.65% |
| **G2** 超时 | `scripts/ohc/conan_verify.py:587` | 硬编码 3600 s；预编译路线（解包 189 MB ＋ 冒烟）预计在内。**PENDING-P2-4** |

## 3. ★ 与 `rust-toolchain` 先例的差异（防止照抄踩坑）

| 项 | `rust-toolchain/1.97.1` | 本骨架 | 为什么 |
|---|---|---|---|
| `export_sources` | **没有** | **有** | G1 是字面量检查，缺了直接 FAIL |
| `apply_conandata_patches` | **没有** | **有**（`build()` 内按 `conandata.yml` 的 `patches:` 列表真应用那 1 条） | 同上 |
| `source()` | 自己拼 `"cur"+"l"` 规避 L0o ＋ `urllib` ＋ 逐候选 sha 校验 | conan 原生 `get()` | `get()` 即可满足；不引入需要"拼接字符串绕过门禁"的写法 |
| 载荷来源 | rust-lang 官方 dist（有官方 URL） | **自建，无官方 URL** | 这是 PENDING-P2-1 的全部由来 |
| `license` | `MIT OR Apache-2.0` | `Apache-2.0 WITH Swift-exception` | Swift 上游的 SPDX 形态 |
| 版本目录 | `archives/r/rust-toolchain/1.97.1/` | `archives/s/swift-toolchain-ohos/6.0.3/` | 包名首字母 `s` |

★ **先例的 `binary` 字段**：`rust-toolchain/commands.json` 写 `"binary": false`
（= 未发布到制品仓）。本骨架同形。

## 4. 落地轮必须做的动作（顺序）

见 `$Q101/records/R-w6-verdict-101.md` 的「落地轮 handoff 一页」。
本档只记录**本目录内部**的两条：

1. `commands.json` 与 `manifest.yaml` 要放到**软件级**目录
   （`archives/s/swift-toolchain-ohos/`），**不是**版本目录 `6.0.3/` 内。
   `conanfile.py` / `conandata.yml` / `test_package/` 放**版本级** `6.0.3/`。
2. `patches/` **要**提交，且**恰含 2 件**：`0001-swiftc-shared-flag-table.patch`（7,968 B）与
   `0002-payload-relocatable-paths.patch`（3,765 B，locale-r112 新增）。
   `export_sources()` 的方法体是 `export_conandata_patches(self)` ⇒ 它导出的是
   `conandata.yml` 的 `patches:` 列表里逐条列出的文件，**不是** `patches/*` 通配符。

## 5. 本轮未做的事（显式登记）

- **未在 `archives/` 下创建任何文件**（0-129：预备件与落地件物理分离）。
- **未跑 `conan create`**（G2）—— 需要真 URL 与 CI 环境；本轮只做**规则级**自查。
- **未签任何二进制**（`sign_elf.py` 不在本轮范围）。
- **未改 P2 定稿**，**未改历史轮根**，**未动任何载荷树**。
