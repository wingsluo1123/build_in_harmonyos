# kio-fuse 5.1.1 适配笔记

> 上游 KDE kio-fuse（FUSE 桥：把 KIO URL 挂载为真实内核 FUSE 文件系统，
> KIO::FileJob / FIO worker 驱动文件 I/O），语言 C++。
> 归档名/分支名 `kio-fuse`，上游仓 invent.kde.org/system/kio-fuse。

## 编译环境
- 构建系统: CMake + Ninja（GNU make 4.4.1 的 mkfifo jobserver 被沙箱拒绝）
- 编译日期: 2026-10-16
- 编译器: clang (OHOS aarch64)，CMake 3.31 + Ninja
- 状态: 真机 create 收官（见文末「真机验证」）

## 适配决策

### 1. Qt6::DBus 接线（补丁 0001 + 0002）
上游 `KIOFuseService` 用 `QDBusConnection`/`QDBusMessage` 走会话总线；而
OHOS 侧 kio/6.26.0 以 `USE_DBUS=OFF` 构建，`KF6KIOConfig.cmake` 不导出
Qt6DBus 传递链接。两处最小补丁：

- **0002（顶层 CMakeLists.txt）**：`find_package(Qt6 ... COMPONENTS Core DBus)`
  —— 版本化别名 `Qt::DBus` 只在创建它的目录作用域可见，tests/ 自己建的
  那个 src/ 够不着，顶层建才有效；
- **0001（src/CMakeLists.txt）**：`target_link_libraries(kio-fuse PRIVATE
  Qt::Core Qt::DBus KF6::KIOCore ...)`。

Qt6DBus 模块本身来自 **qtbase-sql-dbus/6.11.1**（带 FEATURE_dbus=ON 的超集
构建）；qtbase/6.11.1 是 `FEATURE_dbus=OFF`，连 Qt6DBus 的 cmake 文件都
没有。真机上 `--version` 输出的 "KIO FUSE version 5.1.1 / FUSE library
version 3.18.2" 即由此路径产出。

### 2. BUILD_WITH_QT6=ON
kio-fuse 调 `find_package(ECM 5.96)`，ECM 的 QtVersionOption 在请求版本
<5.240 时把 Qt 版本选项默认成 Qt5；KF6 6.26 基线是 Qt6-only，显式打开。

### 3. KDE_INSTALL_LIBEXECDIR=libexec 钉死
ECM 的 KDEInstallDirs 判定「UNIX → libexec，其余 → bin」，设备侧
`CMAKE_SYSTEM_NAME` 让 UNIX 判定失败，守护进程会装进 `bin/`（create #7
实证：test_package 断言 `libexec/kio-fuse` 缺失失败）。generate() 里显式
钉 `KDE_INSTALL_LIBEXECDIR = "libexec"`（CMAKE_INSTALL_LIBDIR=lib 同理），
保持上游/KDE 布局——org.kde.KIOFuse 服务文件的 Exec 与 systemd 单元嵌的
都是这个路径。

### 4. libfuse/3.18.2 静态链接 + 手写 fuse3.pc
制品仓的 libfuse/3.18.2 是 `shared=False, fPIC=True, utils=False` 的静态
包：共享 libfuse3 需要 meson 的符号链（libfuse3.so → libfuse3.so.3.x），
HMDFS 沙箱对 `symlink()` 一律 EPERM，链建不起来；静态归档让守护进程自持
（无 libfuse3 DT_NEEDED，也没有 fusermount3 依赖）。该包已带 HarmonyOS
可移植补丁（pthread_cancel 守卫、挂载路径选择）。

`pkg_check_modules(FUSE3 REQUIRED fuse3)` 需要一个 fuse3.pc：上游源码用
朴素 `#include <fuse_lowlevel.h>`，而依赖生成的 .pc 只暴露
`-I${includedir}`（头在包含子目录 fuse3/ 下），因此在 generators 目录
放置手写 fuse3.pc（libappimage 1.0.4 先例），configure 期把
PKG_CONFIG_PATH 指过去。

### 5. 随包内置 dbus 1.14.10 共享库
OHOS qtbase 的 Qt6DBus 以 `dbus-linked=OFF` 构建，运行期
`dlopen("libdbus-1.so.3")`；而制品仓只发布静态 libdbus-1.a。配方在
build() 里用官方 dbus 1.14.10 源码子构建出共享客户端库（子构建强制
`CMAKE_SYSTEM_NAME=OHOS` 保住 DT_SONAME，过 L5a 门禁），package() 把
`libdbus-1.so*` 三个名字随包。CMake 想用符号链补版本链——沙箱拒绝
`symlink()`——配方以 try/except 回退「复制」物化（构建日志可见
"symlink() EPERM on OHOS: created libdbus-1.so.3 as a copy"）。共享
dbus 包上架制品仓后此段可整体移除（kglobalacceld 6.7.2 先例）。

### 6. DT_NEEDED 绝对路径治理（patchelf）
平台 kcoreaddons/6.26.0 的 `libKF6CoreAddons.so` **无 DT_SONAME**，lld
按导入目标的全路径链接，把构建机的 Conan 缓存路径原样写进 DT_NEEDED：

```
/storage/Users/currentUser/.conan2/p/b/kcore05e7f9b9f84ca/p/lib/libKF6CoreAddons.so
```

绝对路径条目不可移植（L5b 违规），必须在打包前改写。三条路线都实测过：

| 方案 | 结果 |
|---|---|
| `IMPORTED_NO_SONAME TRUE`（补丁给 KF6::CoreAddons 置属性） | **无效**：属性确实进了构建副本（grep 命中 2 处），lld 仍写绝对路径 |
| M3：`-L$<TARGET_FILE_DIR:...>` + `-lKF6CoreAddons` 追加链接项 | 得到裸名条目，但绝对条目**未被去重**（lld 不合并），双条目 → 弃 |
| **patchelf 后处理（采用）** | `--print-needed` 列出绝对条目 → `--replace-needed <绝对路径> <裸名>`。create #9/#10 日志实证 "1 absolute entry rewritten" |

裸名由运行期 LD_LIBRARY_PATH 解析，与其余依赖同一机制。

### 7. 安装后 ELF 重签名（EPERM exec）
cmake.install 会重写已装 ELF 的 RUNPATH，工具链盖的 `.codesign` 段随之
失效，OHOS 内核拒绝 exec() 装载后的守护进程。create #9 实证：test_package
`subprocess.run([daemon, "--version"])` 抛
`PermissionError: [Errno 1] Operation not permitted: .../p/libexec/kio-fuse`
（构建树里的二进制还能跑，装的这个不行——差别只在 install 的 RUNPATH
重写）。package() 收尾重签：`llvm-objcopy --remove-section .codesign`
+ `binary-sign-tool sign -selfSign 1` 遍历包内 ELF（kscreenlocker / kscreen
6.7.2 先例，工具经 compiler_executables 目录 / PATH / /data/service/hnp/bin
三级定位）。

### 8. 上游测试：编译但排除执行
`BUILD_TESTING=ON` 真编译两个 fileopstests（Qt6Test/Qt6DBus 链接 +
qt_add_dbus_interface 代码生成均在构建期被覆盖）；执行被排除，原因是设备
探针实测的沙箱限制：

- 内核 FUSE 挂载被策略拒绝：`open("/dev/fuse")` → EACCES、`mount(2)` →
  SIGSYS/seccomp；
- ctest 命令还套着 `dbus-run-session`，沙箱没有该工具。

`ctest -E "^(fileopstest-cache|fileopstest-filejob)$"`（日志打印排除清单），
守护进程的真实运行行为由 test_package 以消费方视角覆盖（见第 12 节：
脚本真跑 `--version`/`--help`/`-f` + DT_NEEDED/service 文件静态断言）。

### 9. 依赖链修复：kio 包内烘焙的 .cache 路径
libKF6KIOCore.so.6 的 DT_NEEDED 携带 kio 包构建机烘焙的
`/storage/Users/currentUser/.cache/conan2/p/kserv88f93b00a81ef/...` 绝对
路径（kio/6.26.0 已合入的既有形态，非本单问题）：设备本地把
kservice/6.26.0、kcrash/6.26.0 的包目录复制到 `.cache/conan2/p/` 同名
文件夹后，守护进程直接运行输出 `KIO FUSE version 5.1.1` /
`FUSE library version 3.18.2` / `using FUSE kernel interface version 7.45`。
CI farm 上各依赖都从同一台机同一缓存构建，文件夹名确定（`conan download`
复现验证过 `kserv88f93b00a81ef` 文件夹名），无需额外处理。

### 10. 其他配方层固定
- ECM_MODULE_PATH 显式注入（CMakeDeps 生成的 ECMConfig 不传播）；
- 手写 `conan_cmakedeps_paths.cmake`（qtbase/qtbase-sql-dbus 是
  `cmake_find_mode=none`）；
- Ninja 生成器（mkfifo jobserver 被沙箱拒）；
- `libxml2/2.15.3` 显式声明：OHOS SDK lld 对 `libxml2.so.16` 有链接需求，
  需要它的 lib 目录进 LD_LIBRARY_PATH（kio 6.26.0 先例）。

### 11. 源准备（设备镜像 TLS 断的绕法）
设备当前到 download.kde.org 的 TLS 不稳（URLError 104/接力超时），
create 前把 `s/`（source 文件夹）预热：从 conan 下载缓存
（dlcache，sha256 校验过）解出上游树 + 预置 dbus-1.14.10.tar.xz（sha256
校验）+ 把 `es/`（export_sources）内容按 source() 的语义拷进 `s/`。
配方修订号变了换缓存文件夹时，重复同一脚本即可（kf-prep-src3.py）。

### 12. test_package 结构（CI L0c/L0d 合规重构）
首轮 CI 判决 `L0_RESULT=fail: no_test_sources stub_test_method`：test_package
必须有测试源文件（L0c）且 `test()` 需真实调用 `self.run`（L0d/R34 前置）。
据此重构（gnome-recipes / syslog-ng 已合入同型）为两件套：

- **`test_kio_fuse.sh`**（测试源文件，12 断言）：真实执行打包的
  `libexec/kio-fuse` —— `--version`/`--help` 输出断言 + `-f <mnt>` 守挂载
  探针（前台启动、/proc 状态轮询防僵尸、180s 上限；沙箱拒挂时以 libfuse
  诊断优雅退出非零，被许可时保持服务至被杀）；脚本自行补
  `/system/lib64` 与 OHOS SDK `llvm/lib` 到 LD_LIBRARY_PATH、提供可写
  HOME/XDG_RUNTIME_DIR（依赖库路径由 conanrun 环境导出）。
- **`conanfile.py`**（13 断言）：`generators = "VirtualRunEnv"` +
  `self.run(f'sh "{script}" ...', env="conanrun")` 驱动脚本；静态产物断言
  保留在 Python 侧（DT_NEEDED 洁净度、service 文件/systemd 单元路径、
  随包 libdbus-1）——其中随包 `lib/libdbus-1.so*` 断言同时作为 CI R34
  破坏性复跑的反作弊锚点（`lib/` 被移走后测试必然失败，真测试成立）。

## 真机验证（2026-10-16，HarmonyOS PC aarch64 真机；test_package 重构后复验）

conan-verify 全门禁 PASS（`python3 scripts/ohc-run.py conan-verify kio-fuse 5.1.1`，rc=0；
本轮为 L0c/L0d 合规重构后先移除旧二进制再重建）：

- **G0** PASS（知识图谱预查询；E092「CMake 不认识 HarmonyOS 平台」按链上惯例归一处理）；
- **G1** PASS（配方完整性 12 项，含 test_package/ 与 MANIFEST.yml 门禁）；
- **G2** PASS（干净构建：CI profile `ohos-aarch64` + `--user=ohpcd --channel=stable`），包
  `kio-fuse/5.1.1@ohpcd/stable#b6f1f87883f9a3c6a5cc9c2264933493`，
  package_id `fa98c7be7612712c7b287292dd89ae8df602ed0c`——与本单全部独立干净构建
  （同配方另一 ref 的 create 与两轮 G2 重建）逐字一致（可复现；package revision
  因构建目录路径进入产物而随轮次变化，不参与对照）。
- **G3** PASS（R26 系统同名库隔离；无 bin/ 系统库冲突）；
- **G4** PASS（产物完整性；「无法找到程序包 ID」为设备侧无 cache 路径常态注记）；
- **L2/L4/L5** 按设备常态跳过（无 cache 路径），报告随档 `reports/conan-verify-report.md`。

真机构建日志要点（日志本体按平台规则不随库提交、仅本地留档；随档
`reports/conan-verify-report.md`；含重构后 test_package 在 conanrun 环境中的
完整执行）：

```
DT_NEEDED check ...: 1 absolute entry rewritten: .../kcore05e7f9b9f84ca/p/lib/libKF6CoreAddons.so -> libKF6CoreAddons.so
Excluding OHOS-sandbox-incompatible upstream tests: fileopstest-cache, fileopstest-filejob (kernel FUSE mount denied by the app sandbox; dbus-run-session unavailable)
Signed 4 OHOS package ELF file(s)
(test package): Running test()
(test package): static artifact checks OK: DT_NEEDED=['libQt6DBus.so.6','libKF6KIOCore.so.6','libKF6CoreAddons.so','libQt6Network.so.6','libQt6Core.so.6','libc++_shared.so','libc.so']
(test package): runtime probes: test_kio_fuse.sh (run_binary=1)
PASS[1] daemon executable   PASS[2] --version exit 0   PASS[3]/[4] --version 输出断言
PASS[5..7] --help exit 0 + Usage + --disable-filejob-io
PASS[8] -f exited non-zero (rc=1) - sandbox denied the kernel mount
PASS[9..11] no loader failure（error while loading shared libraries / undefined symbol / symbol lookup error）
PASS[12] mount handling: libfuse denied the kernel mount with diagnostics
kio-fuse consumer test: PASS=12 FAIL=0
kio-fuse 5.1.1 test_package: OK
Package 'fa98c7be7612712c7b287292dd89ae8df602ed0c' created
```

test_package（13 项静态产物断言 + 12 项守护进程运行时断言 = 25 检查点全过，TEST_RC=0）。
`--version` 实跑输出 `KIO FUSE version 5.1.1` + `FUSE library version 3.18.2`
（另含 libfuse 运行期探测 fusermount3 被沙箱拒绝的回显，非断言项）。
消费侧行为：daemon 在 conanrun 环境装载运行输出上游版本串（全裸名 DT_NEEDED
解析成功）、`-f` 前台模式按沙箱预期优雅死于 /dev/fuse EACCES（stderr:
`fuse: failed to open /dev/fuse: Permission denied`）；D-Bus 服务文件与
systemd 单元 Exec 路径断言全过。

## 知识沉淀候选（路径 B 待定）
- 无 SONAME 依赖 → 绝对 DT_NEEDED → 三方案对比（属性无效实测）→ patchelf；
- ECM 在非 UNIX `CMAKE_SYSTEM_NAME` 下把 LIBEXECDIR 落到 bin；
- Conan 缓存文件夹名跨机器确定（可复现烘焙绝对路径的可解析性）；
- cmake.install 重写 RUNPATH 失效 .codesign → EPERM exec 的辨识。
