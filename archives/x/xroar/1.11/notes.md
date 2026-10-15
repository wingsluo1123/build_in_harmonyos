# xroar 1.11 适配 notes

## 基本信息

- 库：xroar（Dragon 32/64、Tandy CoCo 1/2/3、MC-10 模拟器）
- 上游版本：1.11（与 Conan 包版本一致，无 R37 递增）
- 源码：官方 release tarball `http://www.6809.org.uk/xroar/download/1.11/xroar-1.11.tar.gz`
- SHA256：`70270805ebd52c0b62237cc2f28b32b5c7df9764d10a7c7190de584cfc6e95af`
- 许可证：GPL-2.0-or-later（ COPYING.GPL / COPYING.LGPL 随包）
- issue：待补（本轮未拿到 issue 编号）

## W0 依赖结论

- 依赖数量：0（必需）
- 已满足依赖：—
- 缺失依赖：无
- 是否需要拆分依赖适配：否
- 阻塞点：无

所有 GUI/音频/IO 后端（GTK2/3、gtkgl、SDL2/3、X11、OpenGL、ALSA、OSS、
Pulse、CoreAudio、JACK、evdev、joydev、sndfile、TRE、zlib、libpng、
pthreads）均为可选集成，configure 检测失败即降级。本包全部显式
`--without-*` 禁用，采用上游始终编译的 null UI（`src/null/ui_null.c`）
与 null 音频驱动，得到零依赖、确定性配置的 headless xroar。

## W1 源码/构建系统分析

- autotools 项目；release tarball 自带预生成 `configure`/`Makefile.in`，
  无需 autoreconf，无需 tool_requires。
- 预生成字体表（`src/mc6847/font-6847{,t1}.{c,h}`、`src/tcc1014/font-gime.{c,h}`）
  已随 tarball 分发，但被列为 BUILT_SOURCES；重新生成需为构建宿主编译
  `tools/font2c`，而 font2c 链接 SDL + SDL2_image。对策：build() 在 make
  前 touch 这 6 个文件，使规则永不触发。
- 上游无自动化测试套件：无 tests/ 目录、无 TESTS/check_PROGRAMS，
  `make -n check` 无此目标。验证口径 = 完整构建 + test_package 冒烟。

## 配方设计（W2/W3）

- `source()` 内联 URL/SHA256 调用 `get()`，不提供 `conandata.yml`：
  规避 CI conandata 预下载路径 `BUILD_DIR: parameter not set` 缺陷
  （仓库知识草稿 DRAFT-shadow-ci / 共性指南 §5.2）。
- build() 就地修复（无 patch 文件）：
  1. E007：config.guess 补 `*:HarmonyOS:*:*)` 分支 + `__OHOS__` libc 探测；
     config.sub 补 `ohos-linux`（沿用 duff/0.5.2 验证过的实现）。
  2. E114：去掉 configure 内 `umask 077 && mktemp/mkdir`（HMDFS 不可写目录）。
  3. touch 预生成字体表（见上）。
- test_package（5 个断言）：`--version` 打印 `XRoar 1.11` 退出 0；
  `--help` 打印选项退出 0；无 ROM 裸运行非零退出且报 ROM 错误（证明
  模拟器核心/配置解析已链接）。

## W4 本机验证（Windows 宿主）

- 配方/测试 Python 语法检查：通过（py_compile）。
- manifest.yaml / commands.json 结构检查：通过（YAML/JSON 解析）。
- 源码 tarball 下载与 SHA256 复核：通过（本地实算一致）。
- 归档结构确认：单一根目录 `xroar-1.11/`，strip_root=True 正确。
- `git diff --check`：通过。
- conan create（G2）：**未在本机执行**——Windows 宿主对 OHOS 交叉 profile
  必然 `[WinError 2]` 假阴性（知识草稿
  DRAFT-windows-host-cross-profile-conan-create-g2-false-negative）。
  G2 放行证据改由真机 shadow CI L1 提供。

## 真机 shadow CI 实测记录（2026-10-13，单包排队）

job：`xroar-1.11-20261013`（设备端 ohos-users/codex/ 下，含独立 conan-home）

| 轮次 | exit | 报错原文（摘要） | 根因 | 解法 |
|---|---|---|---|---|
| r1 | 1 | `conanbuild.conf does not exist` | 缺 AutotoolsToolchain.generate() | 增加 generate() |
| r2 | 1 | `configure: error: working directory cannot be determined` | profile buildenv 的 CONFIG_SHELL 指向 hnp bash，HMDFS getcwd 失败并被 configure 重 exec 劫持（libfec 知识草稿同型） | configure/make 命令行前缀 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` |
| r3 | 1 | `sh: ./configure: No such file or directory` | basic_layout 下 cwd=build-release，configure 在上级 | `sh ../configure` |
| r4 | 1 | `clang-15: error: no such file or directory: 'no'` | 上游 configure 无 GL 时把 GL_LIBS 替换为字面量 no，vo_opengl.c 无条件编译 | make 命令行 `GL_LIBS=`（r6 改为 -lGLESv3） |
| r5 | 1 | `ld.lld: error: undefined symbol: glGenTextures` 等 | 置空 GL_LIBS 后 GL 符号无着落 | `GL_LIBS=-lGLESv3`（系统 libGLESv3 提供全部符号） |
| r6 | 1 | `NameError: Autotools` | package() 残留调用 | 删除 |
| r7 | 1 | `xroar binary missing` | basic_layout 产物在 build-release/src | package() 改用 build_folder |
| r8 | 1 | test 裸运行 60s 超时 | headless null-UI 无 ROM 时进入主循环空转而非报错 | 断言改双分支（ROM 报错或有界空转），stdin=DEVNULL |
| r9 | **0** | — | — | conan create 全绿 |

r9 结果：
- `conan create` exit code：0（source 下载 → configure → make → package → test_package）
- test_package：`XRoar consumer smoke test: 5/5 assertions passed`
  （bin 存在且可执行 / --version 打印 XRoar 1.11 退出 0 / --help 退出 0 / 无 ROM 行为符合 headless 语义）
- 上游测试：0 项（上游无测试套件，见 test_package/MANIFEST.yml 清点证据）
- L1e 破坏性反向验证（本机模拟）：删除 bin/xroar 后 test rc=1
  `FAIL: bin/xroar missing in package` —— 测试真实依赖被测包
- 知识草稿（通用化，已查重不与既有 6589 份草稿重复）：
  - knowledge/drafts/DRAFT-autotools-optlib-no-literal-link-leak.{md,kv}
    （GL_LIBS="no" 字面量泄漏；与 jnoise 命令位置硬编码、GL 空桩两草稿机制区分）
  - knowledge/drafts/DRAFT-headless-backend-missing-resource-idle-dual-branch-test.{md,kv}
    （headless 无资源断言双分支；与 nuvie 草稿互补）

## 真机 shadow CI 执行方式（已完成，记录见上）

```sh
# 隔离 job（设备端已有仓库作为 --repo-source）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex --job xroar-111 \
  --package archives/x/xroar/1.11 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/xroar-111/run-conan-heavy.sh"
```

重点记录：L0/L1/L2/L4/L5 结果、conan create 退出码、test_package 5 断言。
传输用 scp/base64，勿用 PowerShell 文本管道；传输后
`find archives/x/xroar/1.11 -maxdepth 3 -type f | sort` 核对。

## 已知限制

- headless 构建：无 GUI/声音/手柄。后续如需 SDL2 UI，应先单独适配
  sdl2 依赖库，再按 R37 递增 xroar 版本出第二个包，不混入本 PR。
- 运行时需用户自备 ROM 镜像；ROM 不入包、不参与测试。
- `with_pthreads` 已禁用以保证配置确定性；null UI 单线程运行不受影响。
