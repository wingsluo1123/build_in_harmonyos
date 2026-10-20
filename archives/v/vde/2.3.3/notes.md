# vde 2.3.3 鸿蒙 PC 适配记录

## 适配基本信息

- **三方库**：vde (Virtual Distributed Ethernet)
- **版本**：2.3.3
- **上游地址**：https://github.com/virtualsquare/vde-2
- **构建系统**：autotools (autoreconf -fi 自举)
- **适配路径**：路径 A（基础适配）

## 本轮根因分析与修复记录

### 1. 根因分析（为何上轮真机预检报 `无法读取当前 archive 代码树`）
- **现象**：真机验证状态 `incomplete`，失败阶段 `evidence`，提示 `无法读取当前 archive 代码树，不能启动真机预检`。
- **根因**：
  1. 任务名与工作目录为 `vde-2.3.3`，Git 分支名为 `feat/vde-2.3.3`。
  2. 根据 CI 规范（R39/R40/R41），包名必须为 `vde`，路径必须为 `archives/v/vde/2.3.3/`，与分支名 `feat/<库名>-<版本>` 及 conanfile `name = "vde"` 三重严格一致。
  3. 上轮错误地将配方放置在 `archives/v/vde2/` 下，导致真机预检调度器在依据任务/分支定位 `archives/v/vde/2.3.3` 时找不到代码树，预检启动失败。
  4. 同时，根据经验 1 与经验 2（CLI 包满足 L0k/R38 门禁），在软件级目录补充了 `commands.json`。

### 2. 解决方案与实施步骤
1. **规范归档目录**：在 `archives/v/vde/` 下建立完整的配方与元数据结构：
   - 软件级：`manifest.yaml`、`README.md`、`commands.json`（type=tool，声明 vde_switch 等 CLI 工具）。
   - 版本级：`2.3.3/manifest.yaml`、`conanfile.py`、`conandata.yml`、`notes.md`、`test_package/`。
2. **清理误放目录**：将 `archives/v/vde2/` 恢复至 upstream/main 原始干净状态，避免单 PR 跨多个包。
3. **完善配方与测试接入**：
   - `conandata.yml` 增加 `gh-proxy.com` 国内镜像加速与官方原址有序回退。
   - `conanfile.py` 中 `name = "vde"`，配置 `-D__MUSL__`（E091）解决 `sockaddr_storage` 冲突，禁用 OHOS 不支持的 TUN/TAP、wolfssl、libpcap。
   - `test_package` 提供 13 项真实 API 级消费者断言（覆盖 libvdeplug 的 socketpair vdestream 协议往返与 libvdehist 状态机生命周期），输出合规 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）标记。

## 上游测试套件审计结论
- **结论**：上游发布包无内置自动化测试套件（`upstream_tests_exist: false`，口径 `autotools_tests`，N=0）。
- **依据**：根目录与 `src/` 下全量 11 个 Makefile.am 均无 `TESTS`/`check_PROGRAMS`/`check-local`；`configure.ac` 无测试宏；源码树无 `test/` 目录。
- **消费者测试**：`test_package` 补全 13 项硬断言，在真机预检中全部执行并通过。

### 3. 真机编译 pthread_cancel 符号缺失根因与修复
- **现象**：在真机编译 `src/vde_router` 时，链接器报错：
  ```
  CCLD     vde_router
  ld.lld: error: undefined symbol: pthread_cancel
  >>> referenced by vde_router.c
  >>>               vde_router.o:(dhcpd)
  >>> referenced by vde_router.c
  >>>               vde_router.o:(olsr)
  clang-15: error: linker command failed with exit code 1
  ```
- **根因分析**：
  1. HarmonyOS 采用基于 musl 的 libc，未实现 POSIX 线程取消族函数（`pthread_cancel`/`pthread_setcancelstate` 等，见知识库 E085/E127）。
  2. 上游 `configure.ac` 仅探测 `AC_CHECK_LIB([pthread], [pthread_create])`，在 OHOS 上 musl 包含 `pthread_create` 符号导致自动置 `enable_router=yes`。
  3. `vde_router` 是上游专门为 Linux 路由环境编写的守护进程，其内部 `dhcpd` 与 `olsr` 服务使用 `pthread_cancel` 终止后台线程；同时 OHOS 环境缺失虚拟路由所需的底层 TAP 设备支持。
  4. 上游在 `configure.ac` 中原生提供了标准配置选项 `--disable-router`（`AC_ARG_ENABLE([router], AS_HELP_STRING([--disable-router], [Disable libpthread-dependent vde_router compilation]))`）。
- **深度根因分析（为何传 `--disable-router` 依然编译了 `vde_router`）**：
  在调试时发现，即使在命令行显式传入 `--disable-router`，`configure` 仍然打印 `+ VDE Router enabled`。
  审计 `configure.ac` 发现：
  1. `AC_ARG_ENABLE([router], ...)` 使用内部变量 `enable_router`。
  2. 但在 `configure.ac` 的前置库检查中，上游写了：
     `AC_CHECK_LIB([pthread], [pthread_create], [enable_router=yes], ...)`
     这直接无条件将 `enable_router` 变量覆盖为 `yes`！
  3. 当执行到后续的 `AC_ARG_ENABLE([router])` 宏时，`enableval=$enable_router` 读到的值已被污染为 `yes`，导致 `--disable-router` 的判断分支永远无法命中，选项彻底失效！
  4. 同时，上游仅检查 `pthread_create`，未对实际调用的 `pthread_cancel` 做特性检测。
- **解决方案与验证**：
  1. 引入补丁 `patches/0001-configure.ac-pthread-probe-and-clobber.patch`：
     - 将探测结果独立存储至 `add_router_support`（与 `add_cryptcab_support`、`add_over_ns_support` 的上游命名模式一致），消除变量 clobbering 冲突，恢复 `--disable-router` 的开关效力；
     - 将库探测目标对齐为 `pthread_cancel`，使缺乏 cancellation 机制的平台（如 musl/OHOS）能在探测阶段自动将 router 判定为 disabled。
  2. 补丁内零平台宏（无 `__OHOS__`，符合 R8），跨平台行为透明。
  3. 在 `conandata.yml` 中注册该补丁；在 `build()` 中 `apply_conandata_patches(self)` 生效后再进行 `autoreconf -fi` 自举。
  4. 在 `conanfile.py` 的 OHOS 分支 `tc.configure_args` 追加 `"--disable-router"`，裁剪该依赖 pthread cancellation 的可选组件。
  5. 在版本级 `manifest.yaml` 的 `build.configure_options` 追加 `"--disable-router"`，并沉淀相应知识。
  6. 在 `conanfile.py` 的 `package()` 中增强 `autotools.install(args=install_args)`，显式传入 `-j1` 与 `INSTALL=${shim}` 确保安全单线程安装与安装垫片生效。
  7. 核心交付物（4 个公共库 `libvdeplug`、`libvdehist`、`libvdemgmt`、`libvdesnmp` 以及主交换机 `vde_switch` 等 CLI 工具）不受影响，`test_package` 消费端测试 13 项断言保持全绿。
