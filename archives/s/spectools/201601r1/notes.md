# spectools 201601r1 适配笔记（HarmonyOS PC / aarch64 / OHOS）

## 1. 上游与源码

- 上游：Kismet 官方 spectools（Wi-Spy USB 频谱仪工具集）
  <http://www.kismetwireless.net/spectools/>
- 归档：<https://www.kismetwireless.net/code/spectools-2016-01-R1.tar.xz>
  - 2026-10-14 实测 `curl -w '%{http_code}'` → **HTTP 200**，120732 字节
  - `sha256 = 8d70daaf3b4b71196ca63bbd5df0ef14b82c3b496f63b5cfa434fa637dc08d57`
    （与 conandata.yml 一致，实际下载后 `sha256sum` 实测）
- 版本号：上游文件名 `spectools-2016-01-R1.tar.xz` 经 Debian
  uversionmangle（`s/(\d\d\d\d)-(\d\d)-R(.*)/$1$2r$3/`）映射为 `201601r1`。

## 2. 构建矩阵

| 项 | 值 |
|---|---|
| 构建系统 | autotools（tarball 预生成 configure 2.69，无需 autoreconf 自举） |
| host settings | `os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd=17 build_type=Release` |
| 依赖 | `libusb-compat/0.1.7`（0.1.x API 兼容层）、`ncurses/6.6` |
| 工具链 | OHOS clang（`--target=aarch64-linux-ohos`） |
| 产物 | `bin/spectool_raw`、`bin/spectool_curses`、`bin/spectool_net` |

依赖按 W0/R36 预检（`conan download <pkg> -r=ohpcd --only-recipe` 均成功）：

```
libusb-compat/0.1.7  revisions 149f825ecfbaf5b475b12e115307cc06
ncurses/6.6          revisions 3dcfd3b6d759300e8997800cefe8c61f
```

configure 明确拒绝 libusb 1.x（`Libusb 1.x.x not currently supported`），
因此必须用 `libusb-compat`（提供 `usb.h` + `usb_init` 的 0.1 API），
其自身依赖 `libusb/1.0.Z` 由制品仓解析。

## 3. 本地交叉编译（WSL 原生盘）

```bash
cd /root/ohpcd-work/wt-spectools-201601r1/archives/s/spectools/201601r1
conan create . -pr:h=ohos-aarch64-wsl-xbuild -pr:b=default --build=missing
# → spectools/201601r1: Package '4bbdd3f9d367588cf662d8bc961a5547cdbbf653' created
# → test_package build() 用 OHOS clang 编译通过，test() 在交叉构建下按
#    cross_building() 跳过（CI 在 OHOS 原生 worker 上会真实执行）
```

产物实测（`file`）：

```
bin/spectool_raw    ELF 64-bit LSB pie executable, ARM aarch64, 84528 bytes,
                    sha256=0c13137fc538f1a6ea3dbc6aea4d94121dacc6e72c35fb9fa535f18e70ba2502
bin/spectool_curses ELF 64-bit LSB pie executable, ARM aarch64, 470824 bytes,
                    sha256=4adb6c651fec855aa69709167605e921588530ba0eba8c0e5aa72992c30b87f4
bin/spectool_net    ELF 64-bit LSB pie executable, ARM aarch64, 81248 bytes,
                    sha256=6d7cc092e66fca415a0a210e1bb5746e2ca0aa11de12e95dc90fc71016c63fee
```

## 4. 鸿蒙适配要点（补丁逐条）

| 补丁 | 问题 | 处理 |
|---|---|---|
| `0001-config-sub-linux-ohos.patch` | tarball 自带 2001-06-08 版 `config.sub` 不认识 `aarch64` CPU 与 `linux-ohos` OS（E122），`configure` 直接拒绝目标三元组 | 整文件替换为 autoconf 2.71 版 `config.sub`，并在 kernel-os 识别列表补 `linux-ohos`（`judy/1.0.5` 整文件替换先例） |
| `0002-makefile-depend-cross.patch` | `Makefile.in` 的 `.depend` 规则用 `$(CXX) $(CFLAGS) -MM` 对所有 `.c`（含未配置的 GTK 对象）做增量依赖扫描；交叉环境下宿主 CXX 看不到 conan 提供的 usb/ncurses 头 | 禁用依赖扫描（conan 一次性构建无增量需求） |
| `0003-configure-umask022.patch` | `configure` 两处 `umask 077` 在 HMDFS 上产生 setgid 不可写的临时目录（E011/E129） | 剥离 umask 设置（`mfterm` 同款修复） |
| `0004-configure-ncursesw.patch` | ohpcd `ncurses/6.6` 只发布宽字符静态库（`libncursesw.a`，无 `libncurses.a`），configure 的 `-lncurses` 探测失败、`CURSLIBS` 为空 | curses 库检查与 `curseaux` 改为 `-lncursesw`（API 同源，C 代码未使用宽字符接口） |
| `0005-main-return-value.patch` | clang 15 起，C99+ 下 `-Wreturn-type`（非 void 函数裸 `return;`）是**硬错误**：`spectool_raw.c:104`、`spectool_curses.c:93/101/108/114` 直接编译失败 | 5 处 `return;` → `return 0;`（`-h`/非法参数分支，正常退出码语义不变） |

其它交叉构建相关处理（写在 `conanfile.py`，非补丁）：

- **树内构建**：`Makefile.in` 用旧式 `.c.o` 后缀规则，GNU make 后缀规则不做
  VPATH 搜索 → out-of-tree 构建直接 `No rule to make target 'spectool_container.o'`，
  故在源码目录就地 `configure + make`。
- **`make -j1`**：HMDFS 上并行 make 触发 jobserver fifo EPERM（E074，`mfterm` 同款）。
- **显式三元组**：`configure` 仅含 `AC_LINK_IFELSE`（无 `AC_RUN_IFELSE`），
  交叉环境安全；显式传 `--build/--host=aarch64-unknown-linux-ohos`。
- **`CONFIG_SHELL`/`SHELL`/`CC`/`CXX`**：profile `[buildenv]` 写死的
  `/data/service/hnp/bin/bash` 等路径在部分 worker 不存在，经
  `AutotoolsToolchain.environment()` + 路径校验回退覆盖（R33：不裸用未定义的
  shell 变量）。
- **R32**：`settings.os` 判断用 `in ("Linux", "OHOS")`。

## 5. 测试

- 上游**未提供**任何正式自动测试（无 `TESTS` 目标、无测试框架引用、
  无 `test/` 目录），声明见 `test_package/MANIFEST.yml`。
- `test_package/harmonyos_specific_test.c`：编译期 `__OHOS__`/`__aarch64__`
  硬绑定；运行期**纯进程内 ELF64 解析**（不依赖 `readelf`/`objdump`——
  OHOS 运行环境不保证提供这些工具），逐产物 6 项断言 × 3 产物 = 18 项。
  2026-10-14 在 WSL 上用 `qemu-aarch64 -L /opt/ohos-guest`（OHOS guest
  rootfs）**实际执行**该测试二进制，输出：

  ```
  HarmonyOS-specific test: 18 checks, 0 failures
  ```

- `test_package/run_spectools_test.sh`：消费者冒烟——真实执行三个安装产物
  （`-h` 用法、`-l` 设备枚举），全部离线、无需 Wi-Spy USB 硬件。
  **本地无法执行**：本机 guest rootfs 的 musl 缺 `_FORTIFY_SOURCE` 的
  `__fd_chk` 符号（需要 `/opt/ohos-guest/lib/libfdchkshm.so` 预载，
  纯本地仿真 harness 限制，与配方无关）；CI 在 OHOS 原生 worker 上随
  `conanrun` 环境真实执行。脚本判据保守：仅 `126/127`（加载失败）判
  FAIL，其余非零退出码记 WARN（无硬件时设备枚举必然非零）。

## 6. 工具链行为备注（供后续包参考）

- `conan create` **不支持** `-bf/--build-folder`（本地流程 `-of` 与之不同）：
  `conan create -bf DIR` 会报 `unrecognized arguments`。构建目录由 conan
  缓存在 `/root/.conan2/p/b/<pkg><hash>/b/build-release`（同为 WSL 原生盘）。
- 本机 OHOS clang shim（`/opt/lpk-fixed/clang`，模拟 NDK driver）链接出的
  `PT_INTERP` 是 `/lib/ld-linux-aarch64.so.1`，而部分文档预期
  `ld-musl-aarch64.so.1`。OHOS rootfs 两者都在（`/opt/ohos-guest/lib/` 实测），
  故 `harmonyos_specific_test.c` 的断言口径定为「aarch64 动态加载器且非
  x86_64」，避免把加载器命名差异误判成适配失败。
