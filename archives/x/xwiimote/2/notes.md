# xwiimote 2 — 适配笔记

## 1. 上游与产物

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/xwiimote/xwiimote |
| 上游标签 / commit | `xwiimote-2` / `2bc2942a` |
| 源码包 | `xwiimote-2.tar.gz`（sha256 `2e893e28…3975cb`） |
| 构建系统 | autotools（**发行包不含预生成 `configure`**，仅有 `configure.ac` / `Makefile.am`） |
| 主要产物 | `lib/libxwiimote.so.2`、`bin/xwiishow`（ncurses 交互式工具）、头文件 `include/xwiimote.h` |
| 依赖 | libudev（经 libudev-zero 提供）、ncurses（`xwiishow` 需要） |

## 2. 配方设计要点

- **依赖**：`libudev-zero/1.0.4` + `ncurses/6.6`（W0 已确认制品仓可取）。
- **构建文件生成**：`build()` 内先 `mkdir -p m4 && autoreconf -i` 在源码目录生成
  `configure`/`Makefile.in`，再由 `Autotools` 在构建目录 out-of-source 执行
  `configure` / `make -j1`（R9：并行 fork 在沙箱易触发资源限制）。
  *不经上游 `autogen.sh`*：它会自行执行 `./configure --enable-debug`，与 Conan
  参数冲突（`NOCONFIGURE` 语义在本配方场景下不必要）。
- **依赖注入**：上游 `configure.ac` 用 `PKG_CHECK_MODULES([UDEV|NCURSES], …)`。
  `libudev-zero` 的包名与其 pkg-config 模块名（`libudev`）不一致，ncurses 亦不保证
  导出模块，因此 `generate()` 按依赖 `cpp_info` 直接生成 `libudev.pc` / `ncurses.pc`
  到 `generators_folder`——`AutotoolsToolchain` 已把该目录前置进 `PKG_CONFIG_PATH`。
  `configure` 输出确认：`checking for libudev... yes` / `checking for ncurses... yes`。
- **版本号**：上游 `AC_INIT` 与 tag 均为单字符 `2`，Conan 2 的 RecipeReference
  要求版本 ≥ 2 字符（`ERROR: Invalid package version '2'`）。任务卡目录保持 `2`，
  由 `set_version()` 规范为 `2.0`（仓内先例：`archives/c/cutmp3/4` → `4.0`）。

## 3. 适配中解决的问题（按出现顺序）

| # | 现象 | 根因 | 处理 |
|---|---|---|---|
| 1 | `ERROR: Invalid package version '2'` | Conan 版本模式最小长度 2 字符 | `set_version()` 规范为 `2.0`，目录保持 `2` |
| 2 | `'AutotoolsToolchain' object has no attribute …` 调用 `tc.environment.define` | Conan 2.29 中 `environment()` 是方法且每次返回**新** `Environment` 对象 | 放弃环境变量注入，改生成 `.pc`（见 §2） |
| 3 | `configure: error: cannot guess build type` | HarmonyOS 上 `config.guess` 无法识别内核 | OHOS 下显式追加 `--build=<arch>-unknown-linux-ohos`（`config.sub` 已支持该形态） |
| 4 | `config.status: ./confXXX/subs1.awk: Permission denied` | **E129**：HMDFS 对新目录强制 setgid，autoconf 的 `umask 077` 令临时目录连属主都不可写 | 生成 `configure` 后 `sed -i 's/umask 077/umask 022/g' configure` |
| 5 | `checking for libudev... no` | 依赖变量注入未生效（同 #2） | `.pc` 方案后探测通过 |

知识库复用：第 4 项由 `engine` 命中 **E129**（类目 platform/hmdfs），按其推荐方案
`sed-replace` 修复，未新增草稿。

## 4. 上游测试情况（R51 三步法）

**清点**：上游 `xwiimote-2` **无测试套件**，证据见 `test_package/MANIFEST.yml`：
- 源码包顶层只有 `doc/ lib/ res/ tools/`，无 `test/` / `tests/`；
- 根 `Makefile.am` 未定义 `TESTS` / `check_PROGRAMS` / `check-local`，`SUBDIRS = .`
  不含测试子目录，即 `make check` 为空目标；
- 上游 README / DEV 文档未提及自动化测试。

**运行**：上游无测试目标，故 `build()` 只执行 `autoreconf -i` → `configure` → `make`
（`make check` 为空目标，配方未集成，`test_package/MANIFEST.yml` 记录
`upstream_test_in_build: false`），如实记录为 0 项。

**回填**：上游测试 N/N′ = 0/0（无测试）；质量保障由 `test_package` 消费者测试承担。

## 5. 消费者测试（test_package）

三层真实消费者验证，全部 fail-closed（任一断言不成立即 raise）：

**5.1 `test.c`（CMake 目标 `test_xwiimote`）**——确定性断言（不依赖实体 wiimote
设备）：
1. `xwii_iface_new(&iface, NULL)` 必须返回 `-EINVAL`（入参校验）；
2. `xwii_iface_new(&iface, "/nonexistent/…")` 必须返回负错误码且不崩溃；
3. 监视器 `xwii_monitor_new` → `ref` → `poll` → `unref` 完整生命周期（仅在 udev
   枚举能力可用时执行；门禁日志实测 `xwii_monitor_new()` **构造成功**、`poll()`
   返回 NULL——构建机/CI 无 wiimote 实体设备，返回 NULL 属预期行为，故跳过轮询
   断言，只断言"不崩溃 + 资源可释放"）；
4. 监视器可重复构造（对象生命周期无全局污染）。

**5.2 `test_xwiishow_cli.py`（CLI 消费者）**——执行打包的 `bin/xwiishow` 的无头
`list` 路径（不调用 `initscr()`，无 TTY 可跑）与 `-h`，断言真实 stdout 与退出码：
`list` 退出码 0、打印枚举头 `Listing connected Wii Remote devices:` 与
`End of device list`；`-h` **退出码 1**（上游 `main()` **显式处理 `-h`**：
`if (argc < 2 || !strcmp(argv[1], "-h"))` → 打印 `Usage:`、`ret=-1`，
末尾 `return abs(-1)==1`）并打印上游用法文本——退出码与文本各为一条断言。

**5.3 ELF 契约 + 鸿蒙特有签名断言（`_verify_elf_contract()`）**——对 `bin/` 与
`lib/` 下**每个实体 ELF**（跳过符号链接，与主配方签名范围一致）用 `readelf`
断言：架构为 `AArch64`、段表恰含 **1 个 `.codesign`** 段；并断言
`bin/xwiishow` 的 DT_NEEDED 与打包库一致（动态构建断言 `libxwiimote.so`，
静态构建断言 `libudev.so`）。`.codesign` 仅由 HarmonyOS `binary-sign-tool`
写入，通用 Linux ELF 不存在该段，故为真正的平台特有属性。

## 6. 验证记录

| 项 | 结果 |
|---|---|
| `conan create`（profile `ohos-aarch64`，`--build=missing`） | **通过**（exit 0） |
| 交叉编译产物 | `libxwiimote.so.2.0.0` + `bin/xwiishow` |
| `configure` 依赖探测 | `libudev… yes`、`ncurses… yes` |
| `make check`（上游） | 无测试目标（0 项） |
| `test_package`（消费者测试） | **CTest 1/1 通过**；另有 CLI 断言（5 项）与 ELF 契约断言（每个实体 ELF） |
| L2 smoke（`xwiishow --version/--help`） | 修复前 `L2_RESULT=skip: no executables`（签名丢可执行位）；本修复恢复权限后二进制可执行。注：上游 `xwiishow` 对 `--version`/`--help` 不解析参数（走设备打开分支，`return abs(ret)` 非 0），门禁因此仍可能记 skip——见 §7 |
| `.codesign` 签名断言 | `readelf -S` 检出每个实体 ELF 恰 1 个 `.codesign` 段（`test_package/conanfile.py::_verify_elf_contract()` 硬断言，OHOS 分支执行） |

> 本地构建环境修复（**不写入配方**，属本机工具链缺陷）：
> 本机 automake 安装不完整——`Automake/Config.pm` 里 `@datadir@` 未展开、缺
> `ar-lib` 辅助脚本，故本地跑 W3 时临时设
> `AUTOMAKE_LIBDIR=<prefix>/share/automake-1.19` 与
> `ACLOCAL_PATH=<pkg-config>/share/aclocal`。CI 侧工具链完整，配方不做任何环境假设。

## 7. 追加修复（可执行位 / ELF 契约 / CLI 覆盖）

在上一版 head 之上追加的修复（不重写既有提交）：

1. **签名丢可执行位**：`_sign_ohos_elf` 用 `os.replace(output, path)` 时，签名
   工具输出的新文件（实测 `0660`）覆盖了 `install` 出来的原文件（实测
   `0770`），`bin/xwiishow` 与 `lib/libxwiimote.so.2.0.0` 因此**丢可执行位**，
   门禁 L2 报 `skip: no executables`。修复：签名前 `os.stat(path).st_mode`
   记录原权限，`os.replace` 后 `os.chmod(path, mode)` 恢复。
   实测证据：修复前打包件 `-rw-rw----`；签名前构建输出 `-rwxrwx---`。
2. **ELF 契约回归**：恢复 `test_package` 对 `bin/`、`lib/` 下**每个实体 ELF**
   的 `AArch64` + 恰 1 个 `.codesign` 断言，以及 `bin/xwiishow` 的 DT_NEEDED
   断言（fail-closed）。
3. **CLI 覆盖回归**：恢复 `test_package/test_xwiishow_cli.py`（`xwiishow list`
   无头路径 + `-h`）。

> **关于门禁 L2**：上游 `xwiishow` **不匹配** `--version`/`--help`（这两个参数
> 都落到设备打开分支，`main()` 末尾 `return abs(ret)` 为非 0；注意 `-h` **不在**此列，
> 它被上游显式处理、打印 `Usage:` 且退出码 1），且默认动态构建下
> `bin/xwiishow` 需要打包的 `libxwiimote.so.2` 在加载路径上（`-rwx` 冒烟直接
> 执行不带 conanrun 环境时会因库缺失退出 127）。因此即便恢复可执行位，门禁的
> `--version`/`--help` 冒烟仍会记 `skip`；真实的功能性 CLI 覆盖由
> `test_xwiishow_cli.py`（在 conanrun 环境下执行 `list`）承担。仓内同类无
> `--version` 的工具（如 `yank`、`jpnevulator`、`ntfs-3g`、`xpdf`）门禁同样记
> `skip`，非本包独有。

## 8. 后续可改进

- 若上游后续版本自带预生成 `configure`，可移除 `autoreconf` 引导步骤；
- `--build` 三元组目前仅按 `settings.arch` 映射，若扩展到其他 OHOS 架构需补表项；
- 若需门禁 L2 记 pass，需在上游 `tools/xwiishow.c` 增加 `--version`/`--help`
  处理并让 `bin/xwiishow` 自带 RPATH（均超出本次追加修复范围）。

## 9. 追加修复 2（W4 FAIL 处置：镜像前缀 / 声明对齐 / 签名过滤 + CLI 断言）

独立 W4 判定 FAIL 后在上一版 head（`f0a8b1b86d`）之上再次追加（仍不重写既有提交）：

1. **P1（阻断，PF7/R39）镜像前缀**：`conandata.yml` 原第 5 行是第三方提交
   `c8dd17cfcd` 引入的 `https://gh-proxy.com/https://github.com/...` 镜像前缀，
   属 R39/PF7 违规（且门禁预下载实测走了该镜像）。修复：删除该行，只保留官方
   URL；`sha256` 不变（`2e893e28…3975cb`）。
2. **P2 声明对齐证据**：`test_package/MANIFEST.yml` 原写"OHOS 上
   `xwii_monitor_new()` 实测返回 NULL，故跳过"与实测相反——门禁日志
   `当前无 wiimote 设备（预期行为）` 出自**构造成功**分支（`mon != NULL`），
   仅 `poll()` 因无实体设备返回 NULL。修复：按证据改写为"构造成功、poll 返回
   NULL 故跳过轮询断言"，不删证据。
3. **P3① 签名遍历加 ELF 过滤**：主配方 `_sign_ohos_artifacts()` 会对 `bin/`、
   `lib/` 下每个实体文件送签；`-o shared=False` 静态构建时 `lib/libxwiimote.a`
   是 ar 归档（非 ELF），送签会失败。修复：加与 `test_package` 同款的
   `_is_elf()`（魔数 `\x7fELF`）判定，仅签实体 ELF。
4. **P3② CLI 断言对齐**：`test_xwiishow_cli.py` 原 `-h` 分支注释标 `4-5` 但只有
   1 条 check（与实际 4 条总断言数不符），且未断言 `-h` 退出码。修复：补
   `-h` 退出码断言（上游按设计返回 1），使该块恰为第 4、5 条断言；CLI 断言数
   相应由 4 项更正为 5 项。

---

**编译结束**: 2026-10-18 12:15
**最终状态**: built
