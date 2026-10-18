# 桌面集成组件必需化（一）：KF6DocTools 与 SharedMimeInfo

> 适用平台：HarmonyOS PC / OHOS aarch64（conan + CMakeDeps 消费制品仓）
> 关联知识：`knowledge/operations/ohos-adaptation-patterns.md`（平台差异总览）、
> `knowledge/operations/no-desktop-session-dbus-kded/README.md`（会话类集成缺失）
> 首例归档：`archives/p/palapeli/26.04.0`（KDE Gear 拼图游戏，随本主题同 PR 交付）

## 1. 问题：桌面「集成产物」被写成配置期硬依赖

KDE 应用（Gear 全套、Plasma 组件、部分 Extragear 工具）在顶层 CMakeLists 里通常有一张
`find_package(KF6 <min> REQUIRED COMPONENTS ...)` 清单，把**运行期真的会用**的库和
**发行版集成用的产物**混在同一张 `REQUIRED` 清单里。后者在 OHOS 上带来两类配置期失败：

| 现象 | 直接原因 | 典型报错 |
|---|---|---|
| 手册链缺失 | `DocTools` 在 REQUIRED 组件表里，制品仓却没有与该闭包**同线**的 kdoctools | `Could NOT find KF6 (missing: DocTools)` / `Missing the following required components: DocTools` |
| 手册链半删 | 只把组件从 REQUIRED 里去掉，`add_subdirectory(doc)` 与 `kdoctools_install(po)` 仍在 | `Unknown CMake command "kdoctools_create_handbook"` / `"kdoctools_install"` |
| MIME 工具缺失 | `mime/CMakeLists.txt` 里 `find_package(SharedMimeInfo REQUIRED)` | `Could NOT find SharedMimeInfo` |

对 palapeli 26.04.0 的实测（OHOS aarch64，KF6 6.18.0 闭包，未处置时）：

```
CMake Error at .../FindPackageHandleStandardArgs.cmake:227 (message):
  Could NOT find KF6 (missing: DocTools) (found suitable version "6.14.0",
  minimum required is "6.0.0")

      Reason given by package: Missing the following required components: DocTools

Call Stack (most recent call first):
  .../share/ECM/find-modules/FindKF6.cmake:100 (find_package_handle_standard_args)
  CMakeLists.txt:33 (find_package)
```

## 2. 制品仓现状（2026-10 实测，用 `conan list` 直接查）

| 包 | 已发布版本 | 本 profile 有二进制 | 与 6.18 闭包的关系 |
|---|---|---|---|
| `kdoctools` | **仅 6.19.0** | 有（os=OHOS / armv8 / clang 15 / libc++ / cppstd 17 / Release） | **不同线**：6.19.0 拉 `karchive/6.19.0`、`extra-cmake-modules/6.19.0`、`libxslt/1.1.45.1`、`libxml2/2.15.Z`、`openssl/3.5.6.1` |
| `shared-mime-info` | 2.4、2.5.1 | 2.5.1 有 | 不需要同线：ECM 只找 `update-mime-database` 工具 |

**这是本主题与「包根本没发布」的关键区别**：DocTools 不是没包，而是**版本线对不上**。
把 6.19.0 塞进 6.18 图只能靠 `override` 强压，压回去后 `KF6DocToolsConfig.cmake` 仍按 6.19
校验 `KF6Archive`——问题被挪进 conan 图，诊断成本更高。因此 DocTools 走「可选化裁剪」，
SharedMimeInfo 走「官方工具包满足」，两条策略并存（详见 `strategy.md`）。

## 3. 检测：先跑脚本，再动配方

```sh
# 源码树：看配置期硬依赖是否成立
sh knowledge/operations/kf6-desktop-integration/detect-kf6-desktop-integration.sh <源码目录>
sh knowledge/operations/kf6-desktop-integration/detect-kf6-desktop-integration.sh --json <源码目录>

# 构建日志：先复现、再处置（--log 与源码扫描二选一）
sh knowledge/operations/kf6-desktop-integration/detect-kf6-desktop-integration.sh --log <构建日志>
```

判定语义与知识库其它检测脚本一致：**目标平台未声明支持、但源码里当真在用**。

- `HARD`（`exit 1`）——配置期硬依赖，照原样构建必然 configure 失败：
  `DocTools` 落在 `find_package(KF6 ...)` 的组件块内、`find_package(KF6DocTools ...)`、
  `kdoctools_install(`、`kdoctools_create_handbook(`、`add_subdirectory(doc)`、
  `find_package(SharedMimeInfo REQUIRED)`、`update_xdg_mimetypes(`；
  日志侧：`Could NOT find KF6 (missing: DocTools)`、`Missing the following required components: ...DocTools`、
  `Could NOT find SharedMimeInfo`、`Unknown CMake command "kdoctools_*"`。
- 退出码：`0` 未命中 / `1` 命中 HARD / `2` 用法错误。

本机实测（`sh` + busybox awk/grep，OHOS aarch64）：

| 场景 | 输入 | 观测 | 退出码 |
|---|---|---|---|
| 命中 | palapeli 26.04.0 源码树 | `hard=6`：组件表 `DocTools`、`kdoctools_install(po)`、`kdoctools_create_handbook()`、`add_subdirectory(doc)`、`find_package(SharedMimeInfo REQUIRED)`、`update_xdg_mimetypes()` | `1` |
| 命中（日志） | 未处置构建的 configure 日志 | `hard=3`：`Could NOT find KF6DocTools`、`Could NOT find KF6 (missing: DocTools)`、`Reason given by package: ...DocTools` | `1` |
| JSON | 同上源码树 | `python3 -m json.tool` 解析通过，`hard_hits=6`、`hits` 6 条与文本模式一致 | `1` |
| 无命中 | 构造的最小 CMake 工程（无 KF6 组件表） | `hard=0`，`{"hits":[]}` | `0` |

## 4. 处理策略（详见 `strategy.md`）

| 形态 | 策略 | palapeli 采用 |
|---|---|---|
| `SharedMimeInfo` REQUIRED，制品仓有 shared-mime-info | A：`tool_requires("shared-mime-info/2.5.1")`，源码零改动 | ✅ 实测 `Found SharedMimeInfo: .../update-mime-database (found version "2.5")`，包内产出 `mime.cache` |
| `DocTools` REQUIRED，制品仓只有不同线的 kdoctools | B：三处同时裁剪（组件表 / `add_subdirectory(doc)` / `kdoctools_install(po)`） | ✅ `patches/0001-CMakeLists.txt.patch` |

## 5. 复现（双向验证）

```sh
sh knowledge/operations/kf6-desktop-integration/reproduce.sh            # 仓库内 OHOS profile
OHC_CONAN_PROFILE=/path/to/profile sh .../reproduce.sh                  # 覆盖 profile
```

脚本对 `archives/p/palapeli/26.04.0` 跑两轮 `conan create`：

1. **关策略**：把 `conandata.yml` 的 `patches` 临时置空（脚本在临时副本上操作，不改动仓库文件）
   → 期望 configure 失败，日志命中 `Could NOT find KF6 (missing: DocTools)`；
2. **开策略**：补丁登记保留 → 期望 `rc=0`，包内含 `bin/palapeli`、
   `lib/plugins/palapelislicers/*.so`、`lib/plugins/kf6/thumbcreator/palathumbcreator.so`、
   `mime.cache`、`.desktop`、`icons`。

约束（与仓库复现脚本一致）：日志一律重定向到文件、不用管道 `head`（避免 SIGPIPE 误判失败）；
不写死本地绝对路径；每轮使用独立输出目录。

## 6. 样例库

`sample/` 是本主题的最小源码样例（去业务化的三处结构 + MIME 必需化），供检测器自测与
人工对照；真实构建级样例见 `archives/p/palapeli/26.04.0`（同 PR 交付，含 `notes.md` 记录
完整适配链路与限制）。

## 7. 限制与不适用

- 裁剪后**不再交付手册与文档翻译**；需要手册的交付物应在制品仓补发同线 kdoctools。
- 仅适用于「文档/MIME 这类桌面集成产物」。指向运行期真用库的 `REQUIRED`
  （`KIOWidgets`、`Qt6::DBus` 等）不能靠删组件解决，须补依赖。
- `update_xdg_mimetypes()` 在有桌面会话的机器上才有意义；OHOS 侧保留它是为了装机时
  刷新 `mime.cache`，不刷新也不影响程序运行。
- 不覆盖 `kdoctools` 与主程序**同图两条 KF6 线**的强行 override 方案——该方案未在本文档主张，
  如需尝试须单独验证 `KF6DocToolsConfig` 的版本校验行为。
