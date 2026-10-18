# 知识库拓展：依赖包相对 `DT_NEEDED` 致消费方按工作目录解析失败（祖先 bin/ 镜像 + SONAME 重发布）

## 一句话

依赖包共享库未写 SONAME（或链接时给的是路径）时，`DT_NEEDED` 会保留构建期路径字符串；
OHOS 的 musl loader 对**含 `/` 的 `DT_NEEDED` 按进程工作目录逐字解析**，`LD_LIBRARY_PATH`
与 rpath 都不生效，于是消费方（ctest、插件 dlopen、test_package）一换目录就报加载失败。

## 识别条件

命中任一即属本问题（**库名带目录分隔符**是关键判据，裸 `libX.so` 不是本类）：

| # | 信号 | 取证方式 | 命中后处置 |
|---|------|---------|-----------|
| 1 | 运行期报错 `Error loading shared library ../../bin/libKF6ConfigCore.so: (needed by …)`（musl） | 直接读日志；`detect-relative-needed.py --log <log>` | 走策略 S1/S2 |
| 2 | 运行期报错 `error while loading shared libraries: ../../bin/libX.so: cannot open shared object file`（glibc） | 同上 | 走策略 S1/S2 |
| 3 | 依赖包 `readelf -d libX.so` 的 `NEEDED` 含 `../` 或绝对缓存路径 | `detect-relative-needed.py --pkg-root <PKG>` 退码 3 | 走策略 S1（相对）/S2（绝对）/S3（根治） |
| 4 | `QPluginLoader` / `dlopen` 报 `Cannot load library … (libKF6ConfigGui.so: cannot open shared object file)` | 日志中库名带 `/` 时归本类，裸名归 rpath 类 | 走策略 S1 |

判否信号：报错库名是裸名 `libX.so`（属 rpath / `LD_LIBRARY_PATH` / 依赖未安装），或
`ldd` 能解析且程序换目录仍可运行。

## 为什么在鸿蒙 PC 适配中高频出现

- OHOS 工具链默认**不写 SONAME**（见 E1174），任何用该链路发布的包都可能把路径写进 `NEEDED`。
- KF6/KDE 全线分层多、插件化深（`lib/plugins/kf6/...`），消费方式天然跨目录，最先暴露。
- 该缺陷在**发布机自测时不会暴露**（路径真实存在），只在消费方/CI 干净环境暴露，
  因此每个下游库都要独立踩一遍 —— 这正是"共性"的来源，也是本包要收敛的重复劳动。

实测语料（2026-10-18，ohpcd 制品仓 KF6 6.14 段 14 个包）：39 条路径型 `DT_NEEDED`，
34 条绝对缓存路径 + 5 条 `../../bin/` 相对路径，涉及 kconfig / kbookmarks / ki18n /
kcodecs / kguiaddons / kcoreaddons 等；仓库内 **162 个配方**各自手写同一份兼容层。

## 处理策略

| # | 策略 | 侵入性 | 适用 | 实现 |
|---|------|--------|------|------|
| S1 | **祖先 `bin/` 镜像**（相对形态，推荐） | 零侵入：不改依赖包、不改源码 | `NEEDED` 为 `../…` | `apply-compat-shim.py --apply` / 配方 `_make_compat_mirrors()` |
| S2 | **绝对路径镜像**（绝对形态） | 零侵入但要求发布机路径可写 | `NEEDED` 为 `/…/.cache/conan2/…` | 同一脚本，镜像目标即绝对路径 |
| S3 | **依赖包补 SONAME 重发布**（根治依赖侧） | 需改依赖包并重发 | 长期治理；换机后 S2 失效时唯一选择 | `-Wl,-soname,libX.so` |
| S4 | ~~适配方产物侧就地改写 `.dynstr`~~ **实测不可用，禁止** | — | — | 改写后的 `.so` 在本平台 `dlopen` 直接 `Permission denied`（见 `strategy.md` 反例与 E537） |

选型：样例库采用 **S1**（与仓库 162 个配方的既有一致，且 R49 合规——只写私有 build 目录，
不注入共享前缀）；S3 作为回退方案登记（`strategy.md` 含命令模板）。

产物侧的**绝对** `DT_NEEDED` 保持现状，不做任何构建后改写：`ci/conan/build_and_test.sh` 的
L5b 只打印 `[fail]`、写进 ci-metadata.json，`L5_RESULT` 不参与 `FAILED` 计数（致命项为
L0/KC/JC/conan create/L1），已合入的 KF6 包（如 kbookmarks 6.28.0）同样带此类条目。

限制：
- S1/S2 只在安装期/测试期修补运行时解析，依赖包下次发布不修 SONAME 则问题仍在。
- 软链最多上溯 4 层（与插件目录 `lib/plugins` 深度对齐），过深会污染 build 目录祖先。
- HMDFS 下 `ln -sf` 覆盖无效（R5），脚本一律先 `os.remove` 再建链。

## 复现与验证

```bash
# ① 识别：扫描依赖包（退码 3 = 命中）
python3 detect-relative-needed.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests"

# ② 处理：在运行目录各级祖先铺 bin/ 镜像
python3 apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" --apply

# ③ 样例库端到端（无管道，规避 SIGPIPE；日志落盘，退出码即判定）
./reproduce.sh off     # 关闭 SKILL：conan create 必须失败并命中 loader 报错
./reproduce.sh on      # 开启 SKILL：conan create 必须 RC=0

# ④ 检测逻辑自测（fixtures 驱动，无网络/无制品仓）
python3 test_relative_needed.py
```

## 样例库实测数据

| 项 | 值 |
|----|----|
| 样例库 | `archives/b/baloo-widgets/26.04.0`（KDE Baloo Widgets） |
| 依赖链 | KF6 6.14 全线（kconfig/kbookmarks/kiconthemes/ki18n/kio…）+ baloo/26.04.3 |
| 编译器 | OHOS clang（`ci/conan/profiles/ohos-aarch64`），aarch64-linux-ohos |
| 构建系统 | CMake + ECM |
| 关闭 SKILL | `kb_compat_shim=False` → conan create 失败，实测原文 `Error loading shared library ../../bin/libKF6ConfigCore.so: (needed by …/kconf7325dff05dfef/p/lib/libKF6ConfigGui.so)`；全量 ctest 4/6 Failed |
| 开启 SKILL | 默认 → conan create RC=0；全量 ctest 3/6（3 项为依赖包缺 taglib 音频抽取器，与本问题无关）、门禁子集 3/3 |
| 检测脚本命中 | 14 个 KF6 包 → 39 条路径型 `DT_NEEDED`（34 绝对 + 5 相对） |

## 关联知识

- `E1174` — OHOS 工具链默认不写 SONAME（自身产物侧，同机制）
- `E1820` — libjpeg-turbo 斜杠相对 NEEDED 用父目录软链解决（同一手法的早期单点实践）
- `E2080` — KF6 `ki18n_install(po)` 安装期约束（同属 KF6 基线能力缺口，不同问题）
- 条目草稿：`knowledge/drafts/E2296-draft-FD10.kv`（配套 `knowledge/doc/E2296.md`）
