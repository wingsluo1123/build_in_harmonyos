# osdmixer 0.9 适配笔记

## 上游

- 来源：FreeBSD ports `audio/osdmixer`（PORTVERSION=0.9，2007 年合入，作者 Peter Kupietz）。
- 原始 MASTER_SITES：`http://bsd-geek.de/FreeBSD/distfiles/`，已实测不可达
  （本机 `GET osdmixer-0.9.tar.gz` → `RemoteDisconnected`，服务端无响应即断开）。
- 现用权威来源：FreeBSD 官方 distcache 缓存的上游原件
  `https://distcache.FreeBSD.org/ports-distfiles/osdmixer-0.9.tar.gz`，
  本机实测下载 2269 字节，sha256 与 ports distinfo 逐字节一致：
  `615f421850a3eaa0c31375c41da9f6db1d89fd729e775189676ca632a873a98e`
  （SIZE 2269 一致）。conandata.yml 另备区域站点 + 原始 URL 回退
  （playumidi/0.8.3 先例，`verify: false` + sha256 强校验）。
- 包内仅两个文件：`osdmixer-0.9/Makefile`、`osdmixer-0.9/main.c`。
- 许可证：上游包内无 LICENSE 文件、无版权头；FreeBSD port 标注
  `License: not specified in port`。配方 `license` 字段如实填 `Unknown`
  （cdbfasta 先例），不编造。
- 描述：监控 OSS 音量变化，以 OSD 进度条显示 Master/PCM 音量。

## 源码结构（osdmixer-0.9）

- `Makefile`（全文 12 行）：
  `BIN=osdmixer`，`CC?=gcc`，`CFLAGS=-Wall -O3 -pthread`，
  `XOSD=`xosd-config --libs --cflags``；
  目标仅 `all`（单行 cc 编译）、`clean`、`install`
  （`install -Dm 0755 $(BIN) $(DESTDIR)/usr/bin/$(BIN)`）。
- `main.c`（约 200 行）：pthread helper 线程循环
  `ioctl(fd_mixer, SOUND_MIXER_READ_VOLUME/PCM)` 读 `/dev/mixer`；
  主循环用 libxosd（`xosd_create(4)`、`xosd_display` percentage/string、
  `xosd_destroy`）显示两条音量条；`argc<5` 时打印版本/用法并 `return 0`，
  **该路径在 `open("/dev/mixer")` 之后、`xosd_create` 之前返回**，
  不依赖 OSS 音频与 X server；满 5 参数则进入无限监控循环
  （测试时严禁以 5 参数调用）。

## 依赖（W0）

- 唯一外部依赖 `libxosd/2.2.14`（`#include <xosd.h>` + `-lxosd`），在仓库内已适配
  （`archives/l/libxosd/2.2.14`），其传递引入 libx11/libxext/libxinerama/
  xorgproto（X11 栈）。配方 `requirements()` 仅声明 libxosd，R36 干净。
- 其余为系统头：`sys/soundcard.h`（OSS ioctl 号）、pthread（musl 内建）。

## 构建要点（配方等价命令）

```bash
cd archives/o/osdmixer/0.9
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方 `build()` 等价于（`src` 为解压后的上游树）：

```bash
make -j1 CC="<conan conf 的 clang 绝对路径>" XOSD="-I<全部依赖 inc> -L<全部依赖 lib> -lxosd -lX11 -lXext -lXinerama>"
```

- R33：CC 取自 `tools.build:compiler_executables:c`（经存在性校验，
  含 mtu/1.5.1 同款 stale 路径回退），XOSD 由依赖图拼出，
  不执行反引号 `xosd-config`（PATH 不可靠）；make 命令行赋值覆盖
  Makefile 的 `CC?=` 与反引号行；R9 用 `-j1`；`env="conanbuild"`。
- `package()` 不调用上游 `make install`（`install -Dm` 且写
  `$(DESTDIR)/usr/bin`；OHOS 无带 `-D` 的 install(1)，playumidi 先例），
  直接用 Conan `copy` 把编出的 `osdmixer` 装入 `bin/`。
- 无补丁文件（`patches_applied: []`）；`package_type = "application"`，
  `package_info()` 仅保留 `bindirs=["bin"]`；R38 要求的可执行包
  `archives/o/osdmixer/commands.json`（`type: tool`，`binary: true`）已建。

## 上游测试审计（R51 步骤 1，先清点再运行）

| # | 清点源 | 结论 |
|---|--------|------|
| 1 | 源码包根（2269 字节；文件：Makefile、main.c） | 无任何 `tests/`、`test/` 目录或 `*_test.*` 文件 |
| 2 | `osdmixer-0.9/Makefile` | 仅 `all/clean/install` 目标，无 `check/test/TESTS` 目标 |
| 3 | FreeBSD ports `audio/osdmixer` | `do-install` 只装预编译二进制，无 test 目标 |

结论：上游 0.9 **无自动化测试套件**，`upstream_tests_exist: false`、
`upstream_test_total: 0`，口径 `autotools_tests`（手写 Makefile 无 TESTS
注册，`make check` 无规则，等价于空 automake check 目标；与 mtu/1.5.1
同口径）。`build()` 与 `test_package` 均输出 `status: no_tests` 的
`HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed/failed/skipped
全 0，附 reason）。

## test_package（消费者视角，R34）

`test_osdmixer.sh <bin/osdmixer>` 共 5 条断言，只走 help 路径
（零参数与 `48 48` 两个参数，均 `argc<5`），无需 `/dev/mixer` 与 X：

1. 二进制可执行；
2. 裸跑退出码为 0；
3. 输出非空；
4. 输出含 `osdmixer version 0.9` 版本横幅（内容断言，防空文件比空文件）；
5. 部分参数跑退出码为 0。

脚本尾输出 `RESULT: P passed, F failed` 机器 trailer，
`test_package/conanfile.py` 用正则解析该行生成
`HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount 为真实计数）；
无 RESULT 行即抛异常使 `conan create` 失败（harness 失效应可感知）；
任一断言失败脚本以非零退出，conanfile 侧复核后抛异常。
退出码断言是结构性防“静默跳过”手段：help 路径是确定性同步输出，
不存在探测跳过分支。

## OHOS 风险点（待真机预检实证）

- `sys/soundcard.h`：OHOS musl sysroot 是否提供（musl 上游有该兼容头，
  但 SDK sysroot 以实测为准）。若缺失，首选可移植回退补丁
  （`__has_include` 分支 `<sys/soundcard.h>` / `<linux/soundcard.h>`，
  不引入 `__OHOS__` 平台宏，R8/PF5 合规），等真机报错再加，不预判。
- `/dev/mixer` 在 OHOS 运行时不存在：完整监控功能在 OHOS 不可运行，
  属平台能力缺失（`ohos_feature`），help 路径测试不受影响；
  PR 正文补充说明如实声明，不虚报。
- `xosd-config` 脚本：配方已彻底规避（依赖图直拼 flags），
  无论 libxosd 包是否安装该脚本构建均不受影响。
- `install -Dm`：已规避（见构建要点）。

## 状态

- 首轮工作树未提交；`manifest.yaml` 的 `status: built` /
  `build_date` 为通过真机 rule4 门禁后的目标值，待 HMBS 预检确认，
  若预检失败按日志修正配方并同步更新。
- 认领身份（如 PR 模板需填）：GitCode 用户名 `gcw_uQ09W7jl`，队伍名称 `干`。
