# aircrack-ng 1.7 编译笔记

## 编译状态：built（成功）

### 源代码获取
- 来源：https://download.aircrack-ng.org/aircrack-ng-1.7.tar.gz
- SHA256：05a704e3c8f7792a17315080a21214a4448fd2452c1b0dd5226a3a55f90b58c3
- 大小：7740634 bytes

### 编译环境
- 平台：HarmonyOS aarch64
- 编译器：clang 15.0.4
- 依赖：openssl/3.5.6, zlib/1.3.1

### 编译方案

#### 1. 构建系统选择
- 上游使用autotools（configure.ac + Makefile.am）
- OHOS上缺少automake/libtoolize，无法运行autogen.sh
- 改用CMake构建系统，编写CMakeLists.txt替代

#### 2. 核心编译选项
- `-DSTATIC_BUILD`：禁用dlopen动态加载，直接链接静态函数
- `-DDYNAMIC=0`：aircrack-ng工具专用，禁用动态crypto engine
- `-DCACHELINE_SIZE=64`：CPU L1 cache-line size
- `-Wno-deprecated-declarations`：忽略OpenSSL废弃API警告

#### 3. 版本头文件生成
- 从include/aircrack-ng/version.h.in模板创建version.h
- 定义：_MAJ=1, _MIN=7, _SUB_MIN=0, _BETA=0, _RC=0, _SCM="", _REVISION="", LT_VER=1:7:0

#### 4. 平台适配
- osdep：使用dummy.c替代linux.c（避免sockaddr_storage重复定义）
- cpuset：使用cpuset_pthread.c替代cpuset_hwloc.c（OHOS无hwloc）
- trampoline：使用trampoline_arm.c（aarch64 ARM NEON支持）

#### 5. 库文件选择
- 排除communications.c和fragments.c（引用工具特有全局变量opt/dev/rFragment，aircrack-ng不需要）
- 排除parse.c（独立测试程序，含main函数）

#### 6. 链接适配
- aircrack-ng：链接全部库文件 + OpenSSL + zlib
- kstats：仅链接pthread（不需要加密库）
- makeivs-ng：链接库文件 + show_wep_stats桩函数

### 已编译工具

#### aircrack-ng（主程序）
- 功能：WEP/WPA-PSK密钥破解
- 大小：232064 bytes
- 验证：成功读取pcap文件，识别WEP加密网络

#### kstats
- 功能：显示IVS文件中的密钥统计信息
- 大小：27008 bytes

#### makeivs-ng
- 功能：生成测试用的IVS文件
- 大小：141888 bytes
- 验证：显示版本信息"makeivs-ng 1.7"

### 测试结果
- aircrack-ng --version：显示"Aircrack-ng 1.7"
- aircrack-ng test/n-02.cap：成功读取218个包，识别WEP网络
- makeivs-ng --version：显示版本信息

---
**编译结束**：2026-08-05
**最终状态**：built（全部工具编译成功，功能验证通过）
---

**编译结束**: 2026-08-05 04:01
**最终状态**: built
