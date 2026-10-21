# xshogi 1.4.2 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-10-16
- 编译器: clang 15（OHOS aarch64，ohos-aarch64 profile，build=host 原生编译）
- 状态: built（本地 conan-verify + CI 同构门禁通过，未上传制品仓；结果见文末）

## 版本一致性
- 上游 tarball: `https://ftp.gnu.org/gnu/gnushogi/xshogi-1.4.2.tar.gz`
- sha256: `2e2f1145e3317143615a764411178f538bd54945646b14fc2264aaeaa105dab6`
- `configure.ac:8` `AC_INIT([xshogi],[1.4.2],...)` 与任务 version `1.4.2` 逐字一致。

## 构建步骤（conan 驱动）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify xshogi 1.4.2 \
  --profile $HOME/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --project-dir $WORKSPACE
```

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| xorgproto | 2025.1 | X11 协议头（X11/X.h、X11/cursorfont.h 等） |
| libx11 | 1.8.13（override） | libX11.so.6，Xlib |
| libxext | 6.4.0.1 | libXext.so.6（上游 `-lXext`） |
| libxt | 1.3.1 | libXt.so.6，`XtAppInitialize`（上游 `-lXt`） |
| libxmu | 1.3.1.1 | libXmu.so.6（上游 `-lXmu`） |
| libxaw | 1.0.14 | libXaw.so.7，Athena widget（上游 `-lXaw`） |

传递依赖（Conan 自动解析，ohpcd 均有 OHOS/armv8 二进制）：libxpm、libsm、
libice、libxcb、libxau、libxdmcp、xtrans、xcb-proto。全部为 published 依赖，
无未发布父依赖。

## 关键适配点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AC_PATH_XTRA` 在无 xmkmf / 无系统 X11 树的环境走 Imakefile 探测分支 | CI 与真机都没有 xmkmf，也没有系统 X11 开发树（实测 /lib、/lib64、/usr/lib、/system/lib*、$HOME/usr/local/lib 下均无 libX11*） | `generate()` 里经 `AutotoolsToolchain.environment()` 预置 autoconf 缓存变量 `ac_cv_have_x="have_x=yes"`，整段跳过探测；X_CFLAGS/X_LIBS 保持空，头/库路径全部由 `AutotoolsDeps` 注入的 CPPFLAGS/LDFLAGS/LIBS 提供（不写死系统前缀，R26/R49）。比传 `--x-includes/--x-libraries` 更完整——那两项只接受单个目录，覆盖不了 xorgproto+libxaw+libxmu+libxt 的多前缀头文件布局 |
| 2 | `bin/xshogi --version` 无头环境必然非零退出（conan-verify L2 / CI L2 smoke 阻塞） | libXt 1.3.1 的标准选项表**没有** `-help`/`-version`（逐文件核对 `libXt-1.3.1/src/Initialize.c`：仅 -display/-geometry/-name/-reverse/... 等）；上游 xshogi 的 `main()` 先调 `XtAppInitialize`（先开 X display）再判 argc，任何选项都会先撞 `XOpenDisplay` → `Error: Can't open display` → exit 1 | 补丁 `0001-add-version-option.patch`：在 `XtAppInitialize` 之前对 `-version`/`--version` 打印版本并 `exit(0)`。纯追加、无平台宏、非 OHOS 专属；同仓库 X11 GUI 包（xeyes 1.3.1、appres 1.0.7）上游即用同款约定（xeyes.c 在 Xt 之前处理 -help/-version，注释写明"accept single or double dash"） |
| 3 | `config.guess`/`config.sub` 是否需要补 ohos 三元组 | xshogi tarball **不含** config.guess/config.sub，且 configure.ac 未调用 `AC_CANONICAL_*`，configure 只在变量定义处提到 `ac_config_sub` 但从不执行 | 不需要补丁，也不需要传 `--host/--build/--target`（R1 参数最少化；build=host 原生编译） |
| 4 | tarball 里 yacc/lex 产物 | 上游已随包提供 `parser.c`/`parser.h`/`scanner.c`，且比 `parser.y`/`scanner.l` 新 | 不需要 bison/flex；`BUILT_SOURCES=parser.h` 不会触发重建 |
| 5 | GUI 包无头消费者测试 | 设备无系统 X11 .so，二进制 DT_NEEDED 全部由 Conan 依赖提供；XT 程序在无 X server 时必然失败 | test_package 真实执行包内二进制：`--version`/`-version` 断言退出码 0 且输出版本串；无效 DISPLAY 下 `-help` 断言非 0 退出且报 Xt 显示失败诊断（证明真走到 X11/Xt 初始化）。运行库走 conanrun 的 LD_LIBRARY_PATH（主配方 package_info 注入各依赖 libdir），另用依赖包实体 .so 绝对路径 LD_PRELOAD 兜底（HMBS [stale_runtime_library]） |

## 上游测试清点（R51）

- 清点证据见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`：
  - `Makefile.am` 全文无 `TESTS` / `check_PROGRAMS` / `check-local` / `TESTS_ENVIRONMENT`；
  - `Makefile.in` 中 check 相关只有 automake 固定骨架，`TESTS` 展开为空；
  - `configure.ac` 无测试相关宏（无 `AC_CONFIG_TESTDIR`）；
  - 源码包无 `tests/`、`test/` 目录，无 `*_test`/`test_*` 源文件。
- 结论：**上游测试总数 N=0，可运行 N′=0**。`build()` 内仍实际执行 `make check`
  （automake 空套件，无编译、无用例）以留证。
- 因此 L1 测试由 `test_package` 承担：真实执行被测二进制（3 条断言）。

## 验证结果

- conan-verify: `xshogi-verify-20261016-9` exit 0（Verdict PASS；G0/G1/G2/G3/G4 PASS）
- CI 同构: `xshogi-ci-20261016-4` exit 0（L0/L1/L2/L4/L5 + KC + JC 全 pass，Build Summary 1/1 = 100%）
- 逐闸结果与未验证项见本文件"门禁结果"与"平台限制"

## 平台限制（如实申报，未验证项）

- **GUI 功能未验证**：棋盘绘制、菜单交互、与 gnushogi 引擎的本地/远程对局都需要
  X server 与 gnushogi 引擎；真机门禁为无头，`test_package` 只验证"二进制真实执行
  + X11/Xt 链接路径可达"。这不是"编译通过即适配完成"的替代，故在此如实声明。
- **运行期依赖已随包**：设备无系统 X11 动态库（实测 /lib、/lib64、/usr/lib、
  /system/lib*、$HOME/usr/local/lib 均无 libX11*/libXaw*），故 `package()` 把各依赖
  的 117 个 .so 复制进包内 `lib/`，链接期 DT_RPATH=`$ORIGIN/../lib`，包自包含
  （裸环境 `bin/xshogi --version` 实测 rc=0）。
- **conan-verify 的 L2/L4/L5 未真正执行**：工具的 G4 用 `conan list <ref>:*` 后按
  `listing["Local Cache"][<包名>][<ref>]` 取包 ID，而本机 conan 2.29.1 的 JSON 顶层
  键是完整 ref（`xshogi/1.4.2@ohpcd/stable`），取不到 → G4 记 "无法找到程序包 ID"，
  L2/L4/L5 因无 cache 路径而 skip（passed 仍为 True）。这三闸由 CI 同构
  （build_and_test.sh）真正执行：L2 `xshogi --version OK`、L4 patches clean、
  L5 bin/ has content。

## 门禁结果

### conan-verify（job `xshogi-verify-20261016-9`，exit 0）

| 闸 | 结果 | 说明 |
|----|------|------|
| G0 | PASS | 知识图谱预查询（提示 E490：autotools 脚本可执行位，已在 build() chmod 兜底） |
| G1 | PASS | 配方完整性（conanfile/conandata/test_package/MANIFEST.yml 齐全） |
| G2 | PASS | conan create 干净构建成功 |
| G3 | PASS | 无系统同名库冲突（R26） |
| G4 | PASS（⚠️ 无法找到程序包 ID） | 工具侧 ref 解析限制，见"平台限制" |
| L2 / L4 / L5 | PASS（skip） | 因 G4 未取到 cache 路径而跳过；由 CI 同构闸实际执行 |

### CI 同构（job `xshogi-ci-20261016-4`，exit 0，JUNK_PR_DIFF=本库 pr.diff）

| 闸 | 结果 | 说明 |
|----|------|------|
| G0 / G0e | pass | 知识图谱完整性 + 根目录白名单 |
| L0 | pass | L0i 依赖已在制品仓、L0j 版本未占用、L0k commands.json 合规、L0m 目录结构合规 |
| KC | pass | 知识库质量门禁（本次未改 knowledge/） |
| JC | pass | 杂项文件拦截（prdiff 模式；JC6 单软件原子性：1 个软件） |
| L1 | pass | L1a test_package 被执行、L1b 有真实编译/运行痕迹、L1c build 内 make check、**L1e 破坏性反向验证确认测试真依赖被测包** |
| L2 | pass | `xshogi --version OK` |
| L4 | pass | patches clean（无 strcpy/sprintf/gets/strcat） |
| L5 | pass | bin/ has content |
| Build Summary | 1/1 = 100% | Failed: 0 |

### 上游测试（R51）

- 总数 N=0，可运行 N′=0，通过率不适用（无套件）。清点证据见
  `test_package/MANIFEST.yml` 的 `upstream_test_audit`；`build()` 内实际执行
  `make check`（automake 空套件，无用例）留证。
- `test_package` 消费者测试 3/3 通过（真实执行二进制，见 MANIFEST.yml）。
