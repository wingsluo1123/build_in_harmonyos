# indi-pentax 1.0 适配笔记

## 编译环境与准确范围

- 上游：`indilib/indi-3rdparty` 的 `indi-pentax` 子目录，commit `4e700ab0487f1e636a84c927e3e4e368bb1e896a`，2020-06-07，CMake 版本字段 1.0。
- 归档 SHA256：`4852cb98683b95dc88e9a700a12a63bb44bbdcc9aef9bac70a5ae188c71409b2`；Conan 使用官方 codeload 端点并核验。
- 目标：OpenHarmony 6.1.0.115 / aarch64，SDK 26.0.0.18，Clang 15.0.4，libc++，Conan 2.29.1，CMake 4.1.2。官方 profile 的包设置为 `os=OHOS, os.version=6.0, arch=armv8, cppstd=17, Release`，不修改 profile。
- Windows 只负责源码编辑、传输与文档，目标程序在鸿蒙 HiShell 原生编译运行。
- 产物：原驱动 `bin/indi_pentax`、新增 `bin/indi_pentax_image`、`share/indi/indi_pentax.xml` 和许可证。不是整套 INDI 3rdparty 的移植。
- 暂无相机。PTP 在上游 aarch64 默认构建即被排除；硬件 MSC 设置、曝光和传输仍待验收。离线图像消费者不替代硬件验收。

## 复现命令

在官方仓库、该任务独立 Conan 缓存与可执行文件系统运行：

```bash
conan create archives/i/indi-pentax/1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build='indi-pentax/*'
python3 scripts/ohc-run.py conan-verify indi-pentax 1.0
python3 scripts/ohc-run.py finish indi-pentax 1.0 built
```

测试由 `test_package/conanfile.py` 在 `conanrun` 环境调用同目录 `run_tests.py`，仅消费打包程序。该项目只导出 CLI，不虚构头文件或库 API 消费目标。

## 原始失败与修复依据

| 阶段 | 原始行为/失败 | 根因与处理 | 证据 |
|---|---|---|---|
| 原始配置 | CMake 2.8 兼容级别被 CMake 4 拒绝 | 调整最低版本至 3.18 | 原始 configure 日志 |
| 依赖选择 | libev 的另一远端配方选中缺失 ABI | 仅在任务缓存使用赛事远端；依赖已有发布 | W0 下载及原生 install 日志 |
| 原始编译 | 旧 BayerTP、FITS keyword、UploadSettingsTP 接口报错 | 显式适配已发布 libindi 2.2.2.1 | 编译诊断和补丁 |
| pslr 接口 | 旧头文件封装与发布包导出接口不同 | 使用公共 pslr API、移植实际拍摄/读缓冲 helper | capture_helpers.c；符号/头文件审计 |
| 安装运行 | 构建目录能启动、安装目录 EPERM | 安装修改 RPATH 使 ELF 签名失效；build/install 使用相同 RPATH | 安装前后执行对照；既有 E077 |
| 动态链接 | libindi 共享库装载失败 | 发布包同时含静态、动态库；显式选择静态 archives | 链接命令与 ELF 诊断 |
| 静态链接 | 全局 IS* 回调重复定义、离线工具重复 main | 驱动使用 scoped `--wrap` 保持 1.0 分发；离线工具仅替换日志，不引入 INDI main | 链接错误及修复后运行 |
| 可搬迁性 | libraw/libev 绝对缓存路径进入 DT_NEEDED | 已发布库无 SONAME；设置导入目标 IMPORTED_NO_SONAME，链接时使用库名 | 处理前后 readelf；既有 E537 |
| 正式 profile | CMake 原生处理器报告 unknown，误走 Ricoh 源文件并缺 SDK 头 | 改为编译器 __aarch64__ 编译探针，保持原架构范围 | 正式 Conan 编译日志、CMakeSystem.cmake 核验 |
| 平台配置 | CMake 无 Platform/HarmonyOS | 局部模块复用 SDK 的 ELF/POSIX Linux 规则；profile 原样保留 | 既有 E092/E383 |
| 图像错误 | libjpeg 默认错误处理结束进程 | 局部错误处理返回解码失败；临时缓冲成功后才提交，保护旧 CCD 帧 | 无效 JPEG、有效头损坏扫描回归 |
| 临时文件 | 固定 /tmp 文件冲突且权限不同 | TMPDIR 下独立 mkdtemp，创建成功后启动快门；读取保持完整路径 | 源码审计；拍摄端到端待硬件 |

原始日志在仓库外任务交付目录保存；关键测试与机器报告见本目录 `reports/`。前期动态装载失败中，仅判断非零退出码曾产生错误路径假阳性，已替换为精确退出码及诊断断言；旧迭代结果不计入最终通过率。

## 源码修改

补丁由 `refresh-patch --auto` 对原始/工作源码生成，实际文件名以 `conandata.yml` 为准：

| 文件 | 用途 |
|---|---|
| indi-pentax/CMakeLists.txt | Conan 依赖目标、静态 INDI、回调 wrapper、架构编译探针、可搬迁链接、工具安装 |
| indi-pentax/cmake/Platform/HarmonyOS.cmake | 官方 OHOS profile 所用平台名的本地入口 |
| indi-pentax/capture_helpers.c/.h | 真实 pslr 捕获、缓冲读写与 bulb 控制辅助逻辑，无固定成功替代 |
| indi-pentax/indi_pentax.cpp | 新版静态库回调绑定、单次清理注册、枚举句柄回收 |
| indi-pentax/pktriggercord_ccd.cpp/.h | 新 INDI API、状态初始化、私有临时目录、图像失败传播 |
| indi-pentax/gphoto_readimage.cpp | 原读图路径共用、JPEG 事务式缓冲和错误恢复、RAW 布局检查 |
| indi-pentax/image_convert.cpp | 公开离线 JPEG/RAW→FITS CLI，错误码 2/3/4 |

Conan 配方仅支持 Linux/OHOS armv8 的现代依赖组合；实测平台为 OHOS。其余 CPU、旧版依赖组合及 Ricoh 路线不在本配方声明的验证范围。回退为撤销该版本归档或使用固定上游源码；不修改系统库及其他项目。

## 依赖版本及许可

直接依赖：`libindi/2.2.2.1`、`libpktriggercord/0.85.1-20221221181244`、`cfitsio/4.6.4`、`libraw/0.22.1`、`libjpeg/10`、`zlib/1.3.1.1`。

实际参与构建的传递包：`curl/8.15.0.1`、`fftw/3.3.11`、`gsl/2.8`、`libev/4.33`、`libnova/0.16`、`libusb/1.0.27`。依赖二进制来自赛事制品仓，本次没有构建或发布缺失依赖。libindi 使用 shared=False 下发布的静态 archives；libev 明确 shared=True，与已有制品一致。未使用 Ricoh SDK 二进制。

驱动及图像源码 LGPL-2.1-or-later，pkTriggerCord helper LGPL-3.0-or-later；package 中包含两份许可证。SDK EULA 独立，未将其二进制纳入本包。

## 上游测试与消费者

上游目标目录无 tests/、add_test、enable_testing、check 目标。原始自动测试发现 0、执行 0，比例 N/A；相邻第三方驱动和依赖测试不算目标上游用例。

新增 CLI 业务：上层天文图像接收应用调用已安装工具，将输入 JPEG/DNG 转成 FITS，直接解析 FITS 卡片及大端像素，断言尺寸、位深、RGB 平面、灰度值、RGGB 和 DNG 原始像素。另覆盖缺文件、无效 RAW/JPEG、有效 JPEG 头后的扫描错误、已有输出保护、参数契约、INDI XML 无相机枚举。

无相机驱动输入关闭后返回 1 是 INDI `indidrivermain.c::clientMsgCB` 的 EOF 契约；测试同时要求 MSC 枚举、无相机诊断和 EOF 文本，不接受任意非零退出码。测试统计由运行脚本输出并写入 JSON。最终正式结果以 `reports/test-report.md` 及 W3 原始日志为准。

## 平台差异审计

| 类别 | 适用性与实测范围 |
|---|---|
| C/C++ 与架构 | OHOS libc/libc++，编译器目标 AArch64，16-bit RAW 与 FITS 大端转换验证 |
| 线程与调度 | std::async 快门及 INDI 事件循环被编译；实际拍摄时序待硬件 |
| 文件系统 | 私有可执行目录与 TMPDIR；错误输入、已有输出及格式解析实测 |
| 进程/通信 | 驱动 stdin XML/EOF 实测；独立消费者进程调用真实程序 |
| 网络 | INDI 网络服务器属于 libindi，不是本包；本包通信接口为标准输入输出 |
| USB/SCSI | 原生探针可枚举 /dev/bus/usb；/sys/class/scsi_generic 权限错误，/dev/sg0 未见；仅限定当前进程域和无设备条件 |
| 时间 | 拍摄 duration/计时逻辑保留；硬件精度未测试，不填性能结论 |
| 动态装载 | ELF 依赖无私有缓存路径，运行环境由 Conan 导出；制品搬迁另验 |
| 生成工具/JIT | CMake 配置生成 config/XML；无 JIT、自举编译器或目标端代码生成器 |

## 发现与知识

RPATH 签名问题复用 E077；HarmonyOS 平台名复用 E092/E383；SONAME/缓存路径问题复用 E537 及已有草稿。INDI 回调/属性改动是本库对指定依赖版本的接口迁移，本轮不把它直接申报为通用新知识。没有新增 B 草稿，B 分值未申请。本次按 A 路径（基础适配）提交，不申请 C 高难度认定。未声明二进制翻译/PTP 适配成功或完整硬件可用。

## 未完成验收

真实相机的枚举权限、曝光/对焦/设置、JPEG/PEF/DNG 下载、断线重连、长曝光清理与长期运行；厂商 ARM64 PTP SDK 前置条件；平台任务版本映射及 PR/CI/评审。上述项不进入离线消费者通过率的分子，也不以 0 测试套件表示覆盖完成。

## 最终状态

A 路径基础适配提交：正式 OHOS 原生 Conan 构建、安装、10/10 CLI 消费者、缓存外同源复测及 W3 已通过。硬件 MSC 端到端验收仍待真实相机；PTP ARM64 未实现。完整 finish 的框架告警与 W3 通过分别记录，远端 CI 和评审以本 PR 的实际结果为准。
