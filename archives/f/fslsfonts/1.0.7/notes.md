# fslsfonts 1.0.7 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 内置 autoconf 2.72 生成的 `configure`）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，target aarch64-unknown-linux-ohos）
- 状态: built（本地 W3 `conan create` 通过，发布由 CI 完成）

## 编译步骤

标准 Conan 2 配方流程（`conan create . -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`）：

1. `source()`：从 xorg.freedesktop.org（备用 www.x.org）下载 `fslsfonts-1.0.7.tar.xz`
   （sha256 `67cddb1a…c6f306b63`，双镜像实测字节一致），`strip_root=True`。
2. `build()`：先 `apply_conandata_patches()` 打 0001–0003 三个 portability 补丁，
   预置 `PWD=$build_folder`，`autotools.configure()`（configure 探测
   `PKG_CHECK_MODULES(FSLSFONTS, [xproto >= 7.0.25 libfs])` 由 PkgConfigDeps 提供的
   libfs.pc + xproto.pc 满足），OHOS 下把 Makefile 的 `INSTALL` 重定向到 cp/mkdir shim
   （HMFS 上带 `-c` 的 install 会失败，E182/E188），`make -j1`。
3. `package()`：`autotools.install()` 安装 `bin/fslsfonts` 与 `man/fslsfonts.1`，
   清理 `*.la`/`*.o`。
4. `test_package/`：6 条无头消费者断言全部执行并通过
   （`declared=6 passed=6 skipped=0 failed=0`）。

configure 关键读数：`ac_cv_host=aarch64-unknown-linux-ohos`、`host='aarch64-unknown-linux-ohos'`
（0002/0003 补丁真实生效的证据，未使用 `--build/--host` 硬编码）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 报 `unable to guess system type`（uname -s=HarmonyOS）；`config.sub` 拒绝 `aarch64-unknown-linux-ohos`（`OS 'ohos' not recognized`，设备实测 rc=1） | 2024-01-01 版 config.guess/config.sub 不认识 HarmonyOS/ohos | 补丁 0002（config.guess 增 HarmonyOS 分支）+ 0003（config.sub 接受 ohos 记号），平台侧 portability、不写死三元组 |
| 2 | configure 在 `working directory cannot be determined` 一带失败（HMDFS 下 `pwd`/getcwd 不可靠，E011/E114/E386 家族） | HMDFS 构建目录 getcwd 失败 + `config.status` 临时目录 `umask 077` 建出 660 权限 | 补丁 0001：`ac_pwd` 失败时回退 `$PWD`（配方侧同时 `os.environ["PWD"]=build_folder`）、`umask 077→022` |
| 3 | 首轮试跑时 configure 报 `could not make ./config.status`（delimiter 协商循环 6 轮恒 `n=123<num=125`） | 设备 `/usr/bin/sed` 是 toybox sed，其 `s/.*<delim>$/X/` 在**含 UTF-8 多字节字符的行**上失配；当时 CONAN_HOME 用了中文名（`home-主理-4-fslsfonts`），pkg-config 值（FSLSFONTS_CFLAGS/LIBS）嵌入该路径 ⇒ 2 行恒失配 | **CONAN_HOME 改纯 ASCII 命名**（`home-zhuli4-fslsfonts`）后一次通过；CI worker 路径为 ASCII 不受影响。教训：构建目录/CONAN_HOME 一律不用非 ASCII 字符 |
| 4 | `make install` 的手册页安装在 HMFS 上带 `-c` 的 install(1) 失败风险 | HMFS install(1) 不支持 `-c`（E182/E188） | 配方 build() 把 Makefile `INSTALL` 重定向到 cp/mkdir shim（与同族 xcmsdb 1.0.7 先例一致） |

## 源码修改

| 补丁 | 文件 | 类型 | 说明 |
|------|------|------|------|
| 0001-configure-hmdfs-pwd-tmpdir.patch | configure | portability | pwd 回退 $PWD；config.status 临时目录 umask 077→022 |
| 0002-config.guess.patch | config.guess | portability | 识别 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` |
| 0003-config.sub.patch | config.sub | portability | 接受 `ohos-linux` 别名、`ohos*` OS 记号、`linux-ohos*` 内核-系统组合 |

均为平台侧 portability 补丁；上游源码（fslsfonts.c / Makefile.am）零改动。

## 依赖版本

- libfs/1.0.10（提供 `X11/fonts/FSlib.h`、`libFS.so.6`、libfs.pc；经 W0 `conan install --build=never`
  精确复证 ohpcd 已发布二进制，实测下载成功）
- xorgproto/2025.1（提供 `X11/Xos.h`、xproto.pc 7.0.34 ≥ 7.0.25；libfs 传递依赖，配方显式声明）

## 验证结果

```bash
# W3 本地全量（reports/conan-create.log，rc=0）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# PASS 1: binary resolved -> …/p/bin/fslsfonts
# PASS 2: -version -> fslsfonts 1.0.7
# PASS 3: -help usage text printed, rc=0
# PASS 4: no-server path -> 'no font server defined' + usage, rc=1
# PASS 5: unreachable font server -> clean 'unable to open server', rc=0
# PASS 6: dependency closure complete -> libFS.so.6 libc.so
# fslsfonts 1.0.7 test_package: declared=6 passed=6 skipped=0 failed=0
```

上游测试：`grep -cE 'TESTS|check_'` 在顶层 Makefile.am、man/Makefile.am、configure.ac 均为
0（automake 只生成空 check 目标）⇒ N_static=0，无上游对比基线，全部测试为 test_package 自造断言。

## 注意事项

- 运行期能力面：fslsfonts 主功能路径（列出字体）需要可达的 X Font Server
  （`FONTSERVER` 环境变量或 `-s servername`），构建/CI 环境不提供 font server，
  属运行期能力墙，已如实披露；无服务器代码路径（-version/-help/无服务器用法错误/
  服务器不可达干净报错）全部被 test_package 真实断言。
- 构建目录与 CONAN_HOME 路径必须纯 ASCII（toybox sed 对含 UTF-8 行的 `.*…$` 匹配缺陷，见问题 3）。

### 对话 #1（2026-10-15，链主-fslsfonts / 主理-4 窗口）

- W0：`preflight_check.sh fslsfonts/1.0.7` rc=0；`conan install --requires=libfs/1.0.10
  --build=never`（ohos-aarch64 profile）实测从 ohpcd 下载 libfs/1.0.10 + xorgproto/2025.1 +
  xtrans/1.6.0 二进制成功。
- 配方手写（同族 xcmsdb 1.0.7 先例：package_type=application + PkgConfigDeps +
  VirtualBuildEnv + HMFS install shim）；补丁 0001–0003 由 tar 原件逐文件 diff 生成，
  干净树按序实打验证 3/3 通过。
- W3：本地 `conan create` 一次通过（ASCII CONAN_HOME 修正后），test_package 6/6。
- 构建驱动 `build` 一键未采用：其 Step9 以 `force=True` 用模板覆盖手写 conanfile.py
  （driver.py:1137），模板无法表达本包所需（PkgConfigDeps/install shim/application 类型）；
  同族 xcmsdb/xset 均无 build-driver 日志、走 conan-init 探索 + 官方 `conan-verify`（W3）路线。
---

**编译结束**: 2026-10-15 02:48
**最终状态**: built
