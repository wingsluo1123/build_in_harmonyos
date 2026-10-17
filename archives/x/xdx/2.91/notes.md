# xdx 2.91 归档笔记

> 本文件是 archives/x/xdx/2.91 的包级归档笔记：适配决策、踩坑、绕坑命令与
> 验证结论。PR 描述必须与本文件一致。

## 包概况

- xdx 2.91：业余无线电 DX 集群（DX-Cluster / Reverse Beacon Net）telnet
  客户端，C + GTK+3，GNU Autotools 构建，`package_type = application`，
  产物 `bin/xdx`
- 上游：https://github.com/N0NB/xdx（官方发布点 SourceForge
  `xdxclusterclient`）
- 源码：xdx-2.91.tar.gz，sha256
  `4dcba623ba062cb028e67d40a85b9f8eea23259af34ff4752ccc60ca9a2dce7e`
- 上游无测试套件（configure.ac 无 check 目标，源码树无 tests/ 目录，
  已逐一目检）

## 适配决策（零补丁）

1. **`--disable-nls`**：xdx 用 `AM_GNU_GETTEXT([external])`，OHOS 工具链
   无 `msgfmt`/gettext。关闭 NLS 后 UI 字符串回退英文原文；源码以
   `#ifdef ENABLE_NLS` 守卫 `<libintl.h>`，无需引入 gettext 依赖。
2. **`--host=aarch64-linux-gnu`**：2.91 自带的 `config.sub` 不认识
   `aarch64-linux-ohos`（`ohos` OS 未识别），autoconf 直接报错退出。
   覆盖 host 三元组让 autoconf 通过校验；实际编译/链接仍由 profile 的
   `tools.build:compiler_executables`（OHOS clang）完成，产物确为
   aarch64/OHOS（ELF 头实证）。
3. 无补丁：以上两点均为 configure 命令行参数，未动上游一行源码。

## 踩坑与绕坑

### R1 PR #16164 构建 #94384 CI 红：L0a/L0b 缺 test_package

- 现象：`conan-build-test` 步失败于 L0 质量门禁：
  `[fail] L0a: test_package/ directory missing` +
  `[fail] L0b: test_package/conanfile.py missing`（elapsedTime≈1.1s，
  未进入 conan create）
- 根因：首轮 PR 只提交 conanfile.py + conandata.yml；门禁 L0a–L0e 强制
  test_package 四件套（目录 / conanfile.py / 测试源文件 / MANIFEST.yml）
- 处置：补齐 `test_package/{conanfile.py,test_xdx.sh,MANIFEST.yml}`
  （设计见下节）

### R2 OHOS profile 下 `cross_building()` 不可信：按产物 ELF 头判别
（先例 archives/t/tasksh/1.2.0、archives/a/array-hash/0.7.2、
archives/b/breeze-grub/6.7.2）

- 现象：`ohos-aarch64-wsl` 同文件给 `-pr:h`/`-pr:b` → Conan 认为
  host==build，`cross_building()` 恒 False → test 在 x86_64 机器上直接
  exec aarch64 产物 → loader 报 `Error loading shared library
  libc++_shared.so` + 一串 `Error relocating ...: __memcpy_chk/
  __fd_chk/arc4random: symbol not found` → rc=127
- 判别：读产物 ELF 头 `e_machine`（`0xB7`=EM_AARCH64、`0x3E`=EM_X86_64，
  注意 0x3E 是 x86_64 不是 aarch64）与 `platform.machine()` 比对
- 绕坑（emulated 路径，本机 WSL x86_64）：
  ```
  qemu-aarch64 -L /opt/ohos-guest \
      -E QEMU_LD_PREFIX=/opt/ohos-guest \
      -E LD_PRELOAD=/opt/ohos-guest/lib/libchkfcnshim.so:/opt/ohos-guest/lib/libpcmchkshim.so:/opt/ohos-guest/lib/libmemchrchkshim.so:/opt/ohos-guest/lib/libarc4shim.so \
      <xdx 产物>
  ```
  shim 家族（GTK 栈需齐四件，缺一仍 `Error relocating`）：
  - `libchkfcnshim.so`：`__fd_chk/__fread_chk/__fwrite_chk/__str*chk`
    等 glibc-fortify 族
  - `libpcmchkshim.so`：`__memcpy_chk/__memset_chk`
  - `libmemchrchkshim.so`：`__memchr_chk`
  - `libarc4shim.so`：`arc4random/arc4random_buf`（expat 依赖）
  `-E` 只把变量送进 guest 侧，不污染宿主 x86_64 子进程。

### R3 xdx 无显示环境下任何调用都止步于 gtk_init

- `main()` 在 `parse_opts()` **之前**调用 `gtk_init(&argc, &argv)`
  （src/main.c），所以连 `-h`/`-V` 都先挂 gtk_init
- 推论 1：test 不能断言 `rc==0`；headless 合法路径是 `rc=1`
  （gtk_init 失败），有显示则进 GTK 主循环需有界 TERM 收尾（rc=143 合法）
- 推论 2：门禁 L2 烟测（`--version`/`--help`）在本包必然 `[warn]`
  （非阻塞项），属预期
- 推论 3：L1e 破坏性验证靠结构层断言兜底 —— 门禁移走 `bin/` 后
  `_structural_check` 直接 RuntimeError → `conan test` 非零

### R4 本机环境坑（WSL/Git Bash）

- `wsl bash -c '<纯字面>'` 会剥掉 `$VAR`/`$(...)`：脚本逻辑一律走脚本
  文件（`cat 本地文件 | wsl bash -c 'cat > /root/...'`）
- 文件工具 world 限 `C:/Users/13909`：写 WSL/E: 盘需 C 盘暂存 +
  stdin 管道搬运
- `git worktree add` 大仓全量检出 >60s：给足 300s 超时；超时后残留的
  半成品分支要 `git branch -D` 清掉再重建

## test 设计（test_package）

两层验证，全部走 conanrun 环境（包 `bin/` 进 PATH、依赖 `lib/` 进
LD_LIBRARY_PATH）：

1. **结构层**（always，strict）：`bin/xdx` 存在 + 非空 +
   `e_machine==EM_AARCH64` —— 同时保证 L1e 破坏 `bin/` 后测试必失败
2. **运行层**（always，有界启动 ≤5s）：强制动态链接器解析全部
   DT_NEEDED（libgtk-3.so.0 / libglib-2.0.so.0 / libc++_shared.so /
   cairo / pango / harfbuzz / fontconfig / freetype / gdk-pixbuf /
   libpng / libtiff / libjpeg-turbo / zstd …），缺依赖或符号不匹配在
   main() 前报 loader 错误并被断言拒绝；退出码白名单：自退 0/1
   （headless gtk_init），TERM 后 0/1/143（主循环）

- 执行模型：ELF 头判别 native/emulated（见 R2），CI 真机直接执行、
  开发机 qemu 包装 —— 两模型断言完全一致，无降级
- `assertion_count = 5`（结构 3 + 运行 2），与 MANIFEST.yml 一致
- 断言不依赖 readelf/od 等可能缺失的工具（ELF 头由 Python 直接读字节，
  运行层纯 shell 内置命令 + sleep/kill）

## 验证结论

### 2026-10-16 整改轮（lkyz/acc1）

- 本地 `conan create`（`ohos-aarch64-wsl`，WSL ext4
  `/root/ohpcd-work/wt-xdx`）：**rc=0**；`Launching test_package` ✓、
  结构层 OK、emulated 运行层 `rc=1 (headless gtk_init path)` + 全依赖
  解析 ALL PASS（本地日志 `/root/ohpcd-work/xdx_create.log`）
- 产物：ELF 64-bit LSB **PIE** executable, ARM aarch64,
  `BuildID[xxHash]=31660a32007bf4f9`；包引用
  `xdx/2.91#d5dc0edab67b653c7eb1d76c301beb47:dd92520025872d74406bfd869ae688c3862769ac`
- 本地同源门禁（worktree 内跑 `zsh ci/conan/build_and_test.sh`，
  `CONAN_PROFILE=ohos-aarch64-wsl`，含 fresh build）：
  - **L0 pass**（L0a–L0n 全过；L0k commands.json valid type=tool ——
    首轮漏掉 L0k 红过一次，补 `archives/x/xdx/commands.json` 后过）
  - **L1 pass**：L1a test_package 被执行 + L1b 日志证据 + L1e 破坏性
    验证（门禁移走 `bin/` 后测试失败）
  - **L2 skip**（预期内）：`xdx --version/--help` 在 headless 失败
    （gtk_init 先于 parse_opts，见 R3）—— 非阻塞项
  - **L4 pass**（零补丁）/ **L5 pass**（bin/ 有内容）；通过率 100% (1/1)
  - junk_check prdiff：`JC_RESULT=pass`（0 杂项）
- L1e 手工三段式（T424，profile **名** `ohos-aarch64-wsl`；门禁自跑 L1e
  用 profile **文件**路径而仓内无此文件，按 T425 属空壳通过，必须手工
  补证）：pristine rc=0 → 移走 `bin/` rc=1（`RuntimeError: FAIL
  structural: packaged bin/xdx missing`）→ 恢复 rc=0，`L1E_THREEWAY_OK`
- 门禁残留 `.build-cache/`（未被 gitignore）已清理；conandata.yml 经门禁
  镜像注入后已还原为官方 URL（git diff 为空）

## 交付物清单（本 PR，7 文件全在 archives/x/ 下）

- `archives/x/xdx/2.91/conanfile.py`、`conandata.yml`（首轮已有）
- `archives/x/xdx/2.91/test_package/{conanfile.py,test_xdx.sh,MANIFEST.yml}`
- `archives/x/xdx/2.91/notes.md`（本文件）
- `archives/x/xdx/commands.json`（软件级，R38）

### R5 CI #94742（2026-10-16 13:34）：worker 上 config.guess 认不出 HarmonyOS

现象：`conan create` 在 configure 阶段失败：

```
checking build system type... .../build-aux/config.guess: unable to guess system type
...
configure: error: cannot guess build type; you must specify one
ERROR: xdx/2.91: Error in build() method, line 61 autotools.configure()
```

原因：CI 的真实 OHOS worker 上 `uname -s` 返回 `HarmonyOS`，而 tarball 自带的
`config.guess`（2018-02-24 版）不认识该系统 → 无法给出 build 三元组，autoconf 直接
报错。本机 WSL 的 `uname -s` 是 `Linux`，config.guess 正常工作，所以此问题**只在
真实 worker 上暴露**，本地验证发现不了。

处置：在 `generate()` 里显式给出 build 三元组
`--build=aarch64-unknown-linux-gnu`（此前已给出 `--host=aarch64-linux-gnu` 以绕过
config.sub 不认识 `ohos` 的问题；两个三元组都显式给出后，configure 不再调用
config.guess/config.sub 就平台做猜测）。真实编译器仍由 profile 的
`tools.build:compiler_executables` 提供（OHOS clang），产物目标不变。

顺带（house 规则 E074）：`autotools.make()` / `autotools.install()` 钉 `-j1` —— worker
上并行 make 会因 jobserver fifo 被拒而出错，甚至让 make 误判目标已完成而静默不做事
（同批 istgt 的 `make install` 即如此，见 CI #94783）。先例：json-parser/1.1.0、
meterec/0.9.3、vfu/5.09。

### R6 CI #95097（2026-10-16 17:24）：config.status 的 subs1.awk 被拒（HMDFS umask 陷阱）

`--build` 三元组修好之后，configure 走到了 config.status 生成 Makefile 的一步：

```
./config.status: line 628: ./confGMoajN/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

根因：config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录，并在其中生成、
执行 `subs1.awk` 一类辅助脚本；HMDFS 的 umask / uid 映射场景下 077 产生的目录与脚本对构建
进程不可用。**仓内既有处置同款**：quagga、vimpc/0.09.2、istgt/0.4-20111008 的
`_fix_hmdfs_umask()`（把 `umask 077` 改成 `umask 022`）。

处置：新增 `_fix_hmdfs_umask()`，在 `autotools.configure()` **之前**作用于 `configure`
脚本（configure 自己也会做同样的事），**之后**作用于 build 目录下生成的 `config.status`
（后续 make 重新生成 Makefile 时会再次用到）。另把 `save` 加入 `conan.tools.files` 导入。
只改这一处权限设置，不改上游逻辑，不改任何测试与断言。
