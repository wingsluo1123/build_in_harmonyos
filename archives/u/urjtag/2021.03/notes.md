# urjtag 2021.03 适配笔记

## 范围判定
- 上游：http://urjtag.org（项目已迁移到 SourceForge：urjtag）
- 主体语言 C（全树统计：188 .c / 91 .h，无其它语言组件）→ 在 C/C++ 适配范围内
- 产物：liburjtag.a（静态库）+ jtag / bsdl2jtag（命令行工具，静态链入库）
  + share/urjtag/ 器件数据库
- 依赖：libusb/1.0.29（USB JTAG 线缆，ohpcd 共享库）、readline/8.3（命令历史，
  ohpcd 静态库）→ ncurses/6.6（ohpcd 静态库）；三者 `conan download -r=ohpcd
  --only-recipe` 全部可取

## 源码
- 官方发布渠道（三 URL 同一 tarball，conandata 按序尝试）：
  1. https://downloads.sourceforge.net/project/urjtag/urjtag/2021.03/urjtag-2021.03.tar.xz
     （SourceForge 官方项目托管：urjtag 项目页 urjtag.sourceforge.io 即在 SF，
     downloads.sourceforge.net 为其文件发布区）
  2. https://urjtag.org/releases/urjtag-2021.03.tar.xz（项目官网 release 页）
  3. https://distfiles.macports.org/urjtag/urjtag-2021.03.tar.xz（MacPorts
     官方 distfiles，逐字保留上游 release tarball，兜底）
- sha256：b0a2eaa245513af096dc4d770109832335c694c6c12aa5e92fefae8685416f1c
  （1208440 字节）
- 适配网络实测（2026-10-16）：urjtag.org 间歇性完全不可达（HEAD/GET 均超时）；
  downloads.sourceforge.net HEAD 稳定 200 但 body 传输断流；MacPorts distfiles
  一次成功取到完整 tarball。sha256+字节数与官方 Debian .dsc
  （urjtag_2021.03-5.dsc）公布值完全一致，源码身份由独立官方渠道交叉验证

## 构建要点
- tarball 自带预生成 configure（autoconf 2.64 时代 / libtool），无需 bootstrap
- configure 选项：--disable-nls --disable-python --enable-svf --enable-bsdl
  --disable-shared
  - nls：AM_GNU_GETTEXT(external) 会引入 gettext 工具链；@LIBINTL@ 置空即可
  - python：SWIG bindings 在 OHOS 用户态无用且需 python-dev
  - svf/bsdl：tarball 自带 flex/bison 生成产物（.c mtime 新于 .l/.y，
    configure 显式回退 *_bison.h），零再生成，CI 环境不需要 flex/bison
- 静态库（shared=False 默认）：tarball 自带 libtool 对 host_os=ohos 落入
  generic 分支（ld_shlibs=no → can_build_shared=no）且以宿主 x86_64 /usr/bin/ld
  探测交叉 clang，无法产 .so；与仓库 autotools 库惯例一致（a52dec/aalib 均
  shared=False）。jtag/bsdl2jtag 静态链入 liburjtag.a，libusb-1.0.so 仍为动态
  依赖（DT_NEEDED）
- libusb 经 PkgConfigDeps 的 libusb-1.0.pc 定位（PKG_CHECK_MODULES）；
  readline 由 VL_LIB_READLINE 链接探测直接命中（静态库）
- 补丁 0001：configure/config.status 的 `umask 077 && mktemp -d` 临时目录陷阱
  （E011/E114/E129/E136，tanidvr/1.4.1 同款修复），去掉两处 umask 077
- 补丁 0002：config.sub 增加 aarch64-*-ohos* 透传 case（tarball 自带
  config.sub 不识别 aarch64-linux-ohos，a52dec 同款修复）
- 补丁 0003：svf.c 的 ualarm() → 一次性 setitimer(ITIMER_REAL) 替换
  （musl 无 ualarm，语义等价，返回值恒 0 的封装，零平台宏）
- 上游无测试套件（TESTS/check_PROGRAMS 零命中）；`make check` 为空目标，
  build() 中执行留痕

## 本地构建（WSL）
- `conan create archives/u/urjtag/2021.03 -pr:h=ohos-aarch64-wsl-xbuild
  -pr:b=default -c tools.build.cross_building:can_run=true --build=missing`
- test_package 经 qemu-aarch64 -L /opt/ohos-guest（binfmt 亦注册）+ guest
  fortify shim LD_PRELOAD 注入执行，30 项断言全绿

## 已知约束
- CI L2 冒烟为非阻塞项：jtag 裸跑 --version 需要 conanrun 环境提供
  LD_LIBRARY_PATH（libusb-1.0.so）；worker 上打不中仅 warn，真实门禁是
  L0/L1/L1e/L4/L5
- jtag 二进制依赖 OHOS guest loader（ld-musl-aarch64.so.1 /
  ld-linux-aarch64.so.1 两者均可，测试断言已覆盖并存两种）

## CI 修复记录（2026-10-17）

### 根因（5 连红 #96241/#96970/#97096/#97275/#97291）
CI pipeline `ci/conan/build_and_test.sh` 对 `-pr:h` 与 `-pr:b` 传**同一** profile
（`ohos-aarch64`）→ conan 2.29.1 `cross_building()`=False →
`AutotoolsToolchain.__init__` 的自动 triplet 推导在 `if self._is_cross_building:`
之内（autotoolstoolchain.py L76-90）→ 不注入 `--build` 也不注入 `--host`；
`configure_args` 里 `_get_triplets()` 虽无条件拼接，但只有 conf 里有
`tools.gnu:host_triplet` / `tools.gnu:build_triplet` 值才会产出。
两种失败形态：
1. HarmonyOS worker：tarball 自带 2018 config.guess 认不出 `uname -s = HarmonyOS`
   → "cannot guess build type; you must specify one"（#97291 形态）；
2. Linux worker：config.guess 成功，但原生模式（build==host）下尝试运行
   aarch64 OHOS 测试程序跑不了 → "cannot run C compiled programs"（#97096 形态）。
#97275 为 worker 网络类失败（源码下载超时），与配方无关。
本地 `-pr:b=default`（分离 build profile）绿的结论不可迁移到 CI：本地
`cross_building()`=True → triplet 自动注入——这正是差异所在。

### 修复（2 commits）
- e8d74a22：`configure()` 里
  `self.conf.define("tools.gnu:host_triplet", "aarch64-linux-ohos")` ——
  conf 值经 `_get_triplets()` **无条件**输出（non-cross 也生效），
  configure 拿到 `--host=aarch64-linux-ohos`。
  注意：单加 --host 不够——无 --build 时仍会走 config.guess（#97291 实证）。
- 72888ad1：`tc.configure_args.append("--build=aarch64-unknown-linux-gnu")` ——
  build≠host 显式给出 → autoconf 进入 cross 模式，同时跳过 config.guess 与
  "能否运行测试程序"检查，与 worker 类型无关（a52dec 同款修复的完整形态）。
  同时把 test_urjtag.py 第 6 节头文件/器件库检查包进 `if PKGROOT:`
  （conan 路径下 test_package/conanfile.py 恒传 --pkgroot，断言不缩水）。

### 验证证据（2026-10-17）
- 本地 CI 同构 `conan create`（h+b 均 ohos-aarch64-wsl-xbuild，复现 CI 单 profile
  非 cross）：`RUN: configure` 实际命令行含
  `--host=aarch64-linux-ohos ... --build=aarch64-unknown-linux-gnu`，
  test_package 30/30 断言全绿，EXIT=0。
- 本地 cross 回归（`-pr:h=ohos-aarch64-wsl-xbuild -pr:b=default`）：
  30/30 全绿，EXIT=0。
- CI 等价树（upstream/main@ad0c1a73eae + PR head 72888ad1 merge，用 main 的 ci/）
  完整门禁：GATE_EXIT=0，G0 pass（2295 条）/ JC pass / L0 pass / L1 pass /
  L4 pass / L5 pass，Pass rate 100% (1/1)。L2 为非阻塞项，本地 skip
  （aarch64 二进制在 WSL 无法直接跑，CI worker 上原生执行）。
- 分支旧 ci/ 上重跑门禁 G0 假阳性（G0b 三位 E###.kv 正则 vs 新 main 四位
  E#### 条目 586 个 + G0d index 不匹配）——最新 main 的 ci/ 已将 G0b 放宽为
  `E[0-9]{3,}`（不设上限），CI 不受影响；本地跑完整门禁必须在 CI 等价树上
  （merge 最新 main 后用 main 的 ci/），口径与「历史命令在 CI clean 环境里
  逐字可执行」一致。
