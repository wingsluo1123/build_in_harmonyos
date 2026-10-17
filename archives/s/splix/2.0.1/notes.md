# splix 2.0.1 — HarmonyOS PC (OHOS / aarch64) 适配笔记

## 0. 结论

`conan create` 本地交叉编译通过（rc=0），产出两个 aarch64 OHOS 过滤器
（`rastertoqpdl` / `pstoqpdl`）+ 246 个 PPD + 1 个 DRV；消费者测试 17/17
在全链路（真实 CUPS raster 页 → QPDL 作业流）上通过。

## 1. 目标库与语言判定（动手第一步）

* 上游：<https://github.com/OpenPrinting/splix>，release tag `2.0.1`（2024-04-02）。
  SpliX 是 CUPS 打印过滤器驱动，覆盖 Samsung / Xerox / Dell / Lexmark / Toshiba
  的 QPDL（SPL2）打印机。2.0.x 之前的旧主页 splix.ap2c.org 已失效，项目现由
  OpenPrinting 维护。
* 语言判定：发布件解包后后缀分布为 **.cpp ×30 + .h ×29**（另有 246 个 .ppd 数据
  文件、20 个 .defs、5 个 .in、4 个 .po），主体是 **C++**，属本仓库 C/C++ 适配
  范围；无 Go/Rust/Python/JS 主体。

## 2. 取包（官方源，非镜像）

```
curl -sIL -o /dev/null -w '%{http_code}\n' \
  https://github.com/OpenPrinting/splix/releases/download/2.0.1/splix-2.0.1.tar.xz
# -> HTTP 200
# 93032 字节，sha256 533946d57897bf62a2cf8f74e488258e11fa0c55028fad43ada24c5686f38a06
```

解包唯一顶层目录 `splix-2.0.1/` ⇒ 配方 `strip_root=True`。

## 3. 依赖预检（W0，务必先做）

两者都必须同时有**配方**和**已发布 binary**，本机实测：

```
conan download cups/2.4.19   -r=ohpcd --only-recipe   # ok（recipe rev bd8ca05f...）
conan download libjbig/2.1   -r=ohpcd --only-recipe   # ok（recipe rev 2e538386...）
conan install --requires=cups/2.4.19    -pr:h ohos-aarch64-wsl-xbuild -pr:b default -r=ohpcd --build=never
# -> cups/2.4.19: Already installed! (binary 命中)
conan install --requires=libjbig/2.1    ... --build=never
# -> libjbig/2.1: Package installed（从 ohpcd 下载 binary 71fb64d7...）
```

`cups` 是硬依赖（libcups + libcupsimage）；`libjbig` 提供 `libjbig85`，
对应 JBIG 压缩算法（`src/algo0x15.cpp` / `algo0x13.cpp`）。上游允许
`DISABLE_JBIG=1` 关掉，但依赖在制品仓可用，故**不关闭**，保持上游功能完整。

## 4. 构建方案

上游没有 autotools/cmake，只有一套手写 GNU make（`Makefile` + `module.mk` +
`rules.mk`），并且：

* `CC := gcc` / `CXX := g++` 硬编码；
* 通过反引号调用构建机 `PATH` 上的 `cups-config` 取 include/lib 参数，
  并用它推导 `CUPSFILTER` / `CUPSPPD` / `CUPSDRV`。

在 OHOS 交叉编译下这条路径必坏：Conan `cups` 包里的 `cups-config` 是构建时
生成的脚本，`prefix=/`、`includedir=/usr/include`、`libdir=/lib`，会把编译
指向**宿主机的 x86 头文件与库**。cups 本身只有静态库（OHOS 下 `shared=False`），
所以还需要 `-lcupsimage -lcups -lssl -lcrypto -lz -liconv ...` 的**完整且有序**
链接列表。

处理方式（`patches/0001`，仅改 `module.mk` 9 行，无平台宏）：

```diff
-CXXFLAGS += `cups-config --cflags` -Iinclude -Wall -I/opt/local/include
+CXXFLAGS += $(CPPFLAGS) -Iinclude -Wall
-rastertoqpdl_LDFLAGS := `cups-config --ldflags` -L/opt/local/lib
-rastertoqpdl_LIBS    := `cups-config --libs` -lcupsimage
+rastertoqpdl_LDFLAGS := $(LDFLAGS)
+rastertoqpdl_LIBS    := $(LIBS)
（pstoqpdl 两行同理）
-CUPSFILTER := `cups-config --serverbin`/filter
+CUPSFILTER ?= /usr/lib/cups/filter
（CUPSPPD / CUPSDRV / CUPSPROFILE 同理改为 `?=` 常量默认值）
```

配方侧 `generate()/build()` 用 `AutotoolsDeps` 计算 `CPPFLAGS` / `LDFLAGS` / `LIBS`
（含 cups 的传递静态依赖，顺序由 Conan 保证），并以 `deps.vars().apply()` 注入；
`CC` / `CXX` 从 `tools.build:compiler_executables` 取（R33），在 make 命令行上
覆盖（命令行赋值优先于 makefile 的 `CC := gcc`，同时也让所有 `cups-config`
调用不再被执行）。

**不执行上游 `make install`**：该目标依赖构建机的 `install(1)`，并把文件装到
构建机的 CUPS 目录。配方用 `copy()` 显式落盘（`bin/` + `share/cups/model/splix/`
+ `share/cups/drv/` + `licenses/`），交付面与上游 install 等价，但不依赖宿主工具。

## 5. 本地交叉编译证据（WSL 原生盘，非 /mnt）

```
cd /root/ohpcd-work/wt-splix/archives/s/splix/2.0.1
conan create . \
  -pr:h /root/.conan2/profiles/ohos-aarch64-wsl-xbuild \
  -pr:b default -r=ohpcd --build=missing
# CREATE_RC=0
# splix/2.0.1: package(): Packaged 3 files: COPYING, rastertoqpdl, pstoqpdl
# splix/2.0.1: package(): Packaged 480 '.ppd' files（两批 copy 计数之和）
# splix/2.0.1: package(): Packaged 1 '.drv' file: output.drv
# package folder /root/.conan2/p/b/splix7dec70a697924/p
# 日志 /root/ohpcd-work/build/splix-2.0.1/create2.log（311 行，
#   sha256 946f7d5f7dddc6a09c422e1825316036c51e3a02b920aa5bc5e882ad5fa95188）
```

settings：`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd=17 Release`。

制品属性（`file` / `readelf -d`）：

* `bin/rastertoqpdl` — ELF 64-bit LSB **pie executable, ARM aarch64**,
  interpreter `/lib/ld-linux-aarch64.so.1`，8,655,464 B，
  sha256 `ab894371eb8d9e5d08ac03b204597e9568f4133d12556f98d5abaad8ea04745f`
* `bin/pstoqpdl` — 同上，8,395,040 B，
  sha256 `ad1be1cda7f43781f64552e367dd8104d772c878deaa2f38f7badeb86238229b`
* `NEEDED` 只有 `libc.so`（cups/jbig/openssl/zlib/iconv 全部静态链入，无 glibc 依赖，无 rpath 残留）

编译告警只有上游自身的 CUPS 弃用 API（`cupsRasterReadHeader` / `ppdOpenFile` 等）
与 `pstoqpdl.cpp` 未使用变量，均为上游既有，不属本次适配引入。

## 6. 上游测试面：N_static = 0（举证，不是一句 grep）

1. 全树 makefile 只有 `Makefile` / `module.mk` / `rules.mk` / `ppd/Makefile`，
   目标集实测为 `all|debug|optimized|clean|distclean|install|installcms|tags|drv|ppd|cleanppd|optionList`
   —— **没有 `check` / `test` / `ctest` 目标**；
2. 全树 `grep -rnE '(^| )(check|test|ctest)[a-zA-Z_-]*:'` 零命中，`add_test`/`pytest`/`TEST_CASE` 零命中；
3. 上游无 `tests/` 目录、无任何测试源文件；`tools/` 下的 pjl/qpdl 小工具不参与
   构建（`module.mk` 的 `SUBDIRS` 只有 `src`）。

⇒ 如实申报 N_static=0，配方与正文均不声称跑过上游测试。

## 7. 消费者测试（真实执行，非空壳）

`test_package/test_splix.sh`（17 条 pass 站点，由 `conanfile.py:test()` 调用并透传退出码）：

* **S1** 两个 filter 在 PATH 上、可执行、非 stub（>=1MB），ELF 头为 64-bit LE aarch64（e_machine=0xb7）；
* **S2** `ml2250.ppd` 存在、PPD 总数 246、`share/cups/drv/output.drv` 存在，
  且 PPD 内 `*FileVersion: "2.0.0"` 与二进制内 `PPDVERSION` 一致；
* **S3/S5** `rastertoqpdl` / `pstoqpdl` 无参数时退出码 1 并打印 `Usage: ... job-copies options [file]`；
* **S4（最强一条）** 用真实 CUPS raster 页跑端到端：

```
PPD=<pkg>/share/cups/model/splix/ml2250.ppd \
  rastertoqpdl 1 tester "splix test" 1 "" test_package/sample-8x8.raster.b64（base64 文本，运行时解码为字节一致的临时文件） > page.qpdl
# rc=0；982 字节 QPDL 流
# 首尾均为 PJL 通用退出序列 ESC%-12345X
# 含 "@PJL ENTER LANGUAGE = QPDL"
```

`sample-8x8.raster.b64（base64 文本，运行时解码为字节一致的临时文件）`（1864 B，sha256 `5c59fcee8de9327f301be89accf54370ad5b42a4e3f0a55a31d1d3e21e220e1d`）
由 CUPS raster API（`cupsRasterOpen` + `cupsRasterWriteHeader2`）按该 PPD 的
`*ColorModel Gray: <</cupsColorSpace 3 / cupsCompression 17>>` 生成，
`cupsCompression = 0x11`（17）——这正是 `compressPage()` 支持的 QPDL 算法之一。
**注意**：CUPS raster 文件与机器字节序无关（内含反向同步字 + 逐字段 htonl），
所以这个样例在任何架构上生成的字节流是一致的、可长期固化的测试输入。

本机在 WSL 上用 qemu 实跑（离机环境受限，故用 guest musl rootfs 补齐 OHOS libc 符号）：

```
PATH=<pkg>/bin:$PATH QEMU_LD_PREFIX=/opt/ohos-guest \
  LD_PRELOAD=libfdchkshim.so:libarc4shim.so \
  sh test_package/test_splix.sh <pkg>
# -> 17 PASS / TEST_RC=0
```

`libfdchkshim.so` / `libarc4shim.so` 是 /opt/ohos-guest 里的**本地验证用** shim
（真机 OHOS libc 自带 `__fd_chk`、`arc4random`），**不随包交付**。

## 8. 已知问题 / 风险（如实申报）

1. **上游 2.0.1 没改版本宏**：`include/version.h` 仍是
   `VERSION "2.0.0"` / `PPDVERSION "2.0.0"`。即 `rastertoqpdl` 启动日志会打印
   "SpliX filter V. 2.0.0"，PPD 的 `*FileVersion` 也是 2.0.0。这不是本次适配
   引入，也未打补丁（改上游版本宏不在适配范围）。消费者测试按 **2.0.0** 断言，
   与制品实测一致。
2. **`pstoqpdl` 的 `RASTERDIR` 是编译期常量**：上游用
   `-DRASTERDIR="/usr/lib/cups/filter"` 并在运行时 `execl(RASTERDIR "/rastertoqpdl")`
   与 `RASTERDIR "/pstoraster"`。本包把过滤器装在 `bin/`（Conan 包惯例，
   也便于 CI 的 bin/ 门禁与 PATH 消费），因此**部署到真机时**需要把
   `bin/*` 放到 `/usr/lib/cups/filter/`（或做等价软链），`pstoqpdl` 才能找到
   `rastertoqpdl`；另外它还需要来自其他包的 `pstoraster`/`gstoraster`
   （cups-filters/ghostscript），本包不含。这是运行期部署约定，已在
   manifest.yaml 记录。
3. **二进制未 strip**：上游 optimized 目标带 `-g`，两个 filter 各约 8MB
   （静态链入 openssl 等）。若需要瘦身，可在 `package()` 里加 strip 步骤
   （本轮保持上游默认，不引入额外改动）。
4. 上游 PPD 清单与 `ppd/Makefile` 的型号列表并不完全一致：`ppd/` 里没有
   `ml2160/ml2165/ml3310*`（它们在发布件根目录），而 `ppd/Makefile` 的
   `SAMSUNG` 列表里却列了 `ml2160`。本包两处都交付（共 246 个 PPD，无重名），
   绕开这个上游不一致。

## 9. 后续人工事项

* 认领平台任务后提交本 MR；CI 为评论触发型，认领后需在 MR 下发 `/rebuild`。
* 真机（OHOS + CUPS 环境）验证：把 `bin/` 部署为 `/usr/lib/cups/filter/`，
  用真实 raster 作业打印一页；`pstoqpdl` 路径需要 `pstoraster`/`gstoraster`。
* 制品仓发布（`conan upload`）后，把 `archives/s/splix/commands.json` 中
  `2.0.1.binary` 置 `true`，版本级 `manifest.yaml` 的 `status` 升 `published`。
