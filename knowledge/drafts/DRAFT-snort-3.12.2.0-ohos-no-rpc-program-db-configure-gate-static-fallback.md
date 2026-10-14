# DRAFT-snort-3.12.2.0: OHOS musl 无 RPC program number database——上游以其为 configure 硬门时需平台分支降级（静态端口模式保留）

- **条目 ID**: `DRAFT-snort-3.12.2.0-ohos-no-rpc-program-db-configure-gate-static-fallback`
- **严重度**: 2（🟡 中等）
- **类别**: cmake, portability, libc, ohos, network
- **触发工具/阶段**: cmake | conan | cxx | clang — configuration / build / runtime
- **来源**: snort 3.12.2.0 适配（feat/snort-3.12.2.0，OHOS PC aarch64）
- **路径**: Path B（知识库扩展）
- **关联**: [[DRAFT-13904-swiftshader-musl-glibc-only-apis]]（同族：musl 缺 glibc 扩展——彼为编译期声明缺失的替换/守卫，本条目为链接期符号与数据库双缺失下的 configure 硬门降级）；[[DRAFT-libnss_nis-3.4-glibc-nss-compat-headers]]（同族：glibc 专有后端接口缺失）

## 症状

snort 3.12.2.0 在 OHOS 真机配置期（`cmake` 驱动）直接中止：

```
CMake Error at cmake/sanity_checks.cmake:51 (message):
  Couldn't find an RPC program number database implementation!
```

上游逻辑（`cmake/sanity_checks.cmake`，经顶层 `CMakeLists.txt` include 进入配置期）：先试 glibc 内建 `check_function_exists(getrpcent
HAVE_TIRPC_GETRPCENT)`，命中则 `USE_TIRPC`；两者皆否时 `message(SEND_ERROR ...)`
——在没有第三条平台出路的系统上，configure 是硬失败而不是降级。

## 根因

HarmonyOS 的 musl 系 libc 不提供 glibc 的 RPC program number database，
**系统层 API 与数据库文件双缺**（libtirpc 包在制品仓可得，探针 3 已于
2026-10-04 复测修正），真机探针（2026-10-03 首测）：

1. **头文件缺失**：`#include <rpc/netdb.h>` 编译即败（设备 clang 15.0.4）：

   ```
   rpcprobe.c:1:10: fatal error: 'rpc/netdb.h' file not found
   ```

   设备 `/usr/include/rpc` 目录本身不存在。

2. **符号缺失**：`check_function_exists(getrpcent)` 恒 FALSE（CMake 4.1.2 实测，
   探针工程输出 `HAVE_GETRPCENT=[]`）。该探测是**链接期**检查——判假说明
   libc 里没有 `getrpcent` 符号，所以「运行期空返回容错」这条路不存在：
   任何调用它的代码在该平台链接不起来。

3. **无 `/etc/rpc` 数据库文件**：`ls /etc/rpc` → `No such file or
   directory`（2026-10-04 复核）。libtirpc 可得性另行复测（同 2026-10-04）：
   `conan list 'libtirpc/*' -r=ohpcd` → `libtirpc/1.3.7`（**制品仓可得**）。
   早前不加 `-r` 的查询只搜本地缓存，`no matching` 的"无移植"结论错误，已修正
   ——同库 `DRAFT-irpas-0.10` 经 `-r=ohpcd` 使用 `libtirpc/1.3.7` 的先例即正确记录。

因此数据链是：本平台既无 `/etc/rpc` 数据库文件也无对应 API。依赖「运行期
枚举 RPC 程序号」的功能（snort 的 `service_rpc` 检测器会用 `getrpcent()` 从
数据库展开 程序号→服务 映射）在该平台上只能降级为**静态映射**。

两层后果：

- **配置层**：上游把数据库当硬门 ⇒ `SEND_ERROR`，configure 直接失败；
- **源码层**：即使绕过硬门，消费端枚举无源码保护（`service_rpc.cc` 的
  `getrpcent()` 循环）也无法编译——头文件都没有。

## 影响面（affected_scope）

HarmonyOS/OHOS（musl 系 libc）上，一切把 RPC program number database 当
configure 硬门、或直接调用其 API 的 C/C++ 项目：

- **探测门型**：autoconf/cmake 用 `check_function_exists(getrpcent)` / 头文件
  探测（`<rpc/netdb.h>`）判定 RPC 支持，双路皆否时 `SEND_ERROR`（cmake）或
  `AC_MSG_ERROR`（autoconf）中止配置——snort 3.12.2.0 实测全覆盖；
- **消费型**：任何依赖运行期 `getrpcent()/getrpcbyname()` 枚举做 程序号→服务
  映射的功能模块（该平台链接期即无该符号，无运行期容错空间）；
- **判定探针**（任取其一即可确认受影响）：头文件缺失 / 链接期符号缺失 /
  无 `/etc/rpc` 数据库文件——三者均为平台事实，与具体库无关；libtirpc
  路线在制品仓可得（`-r=ohpcd`，`libtirpc/1.3.7`），需要保留动态枚举的
  消费方可显式引入该依赖（本适配选择不引入，理由见「已试过的失败方案」）。

## 最小复现

```sh
# 探针1：头文件（设备 hnp clang）
printf '#include <rpc/netdb.h>\nint main(void){struct rpcent* r=getrpcent();return r==0;}\n' > rpcprobe.c
clang rpcprobe.c -o rpcprobe
#   → fatal error: 'rpc/netdb.h' file not found

# 探针2：CMake 链接期探测（设备 cmake 4.1.2）
#   CMakeLists.txt: include(CheckFunctionExists); check_function_exists(getrpcent HAVE_GETRPCENT)
#   → HAVE_GETRPCENT=[]（假；libc 无该符号）

# 探针3：数据库文件 + libtirpc 可得性（2026-10-04 复测修正）
ls /etc/rpc
#   → No such file or directory
conan list 'libtirpc/*' -r=ohpcd
#   → libtirpc/1.3.7（制品仓可得；勿省略 -r——否则只查本地缓存）
```

## 已试过的失败方案

1. **运行期容错**（判空返回即降级）：不可行——探针2 是链接期检查，
   `getrpcent` 符号在平台 libc 中不存在，调用代码链接即败，运行期根本到不了。
2. **引入 libtirpc 依赖**：制品仓可得（`libtirpc/1.3.7`，见探针3 与库内
   `DRAFT-irpas` 先例），但本适配选择**不引入**：本平台无 `/etc/rpc` 数据
   文件，引入后运行期动态枚举仍无数据可读；为单一检测器扩展依赖链收益低。
   上游的 `USE_TIRPC` 第二条路在有该需求的消费方处依然可走通。

## 解决方案

**CMake 配置侧**（patch `0001-cmake-optional-libs-ohos.patch`，平台分支）：

```cmake
    check_function_exists(getrpcent HAVE_TIRPC_GETRPCENT)
    if (HAVE_TIRPC_GETRPCENT)
        set(USE_TIRPC TRUE)
    elseif (CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
        # The HarmonyOS/OHOS libc exposes no RPC program number database;
        # libtirpc is available in the registry but intentionally not used
        # here (see notes.md).  Propagate that decision to the one consumer
        # (service_rpc.cc): when SNORT_NO_RPC_DB is defined its getrpcent()
        # enumeration is compiled out, keeping the static port patterns only.
        add_definitions(-DSNORT_NO_RPC_DB)
        message(STATUS "RPC program number database missing on HarmonyOS/OHOS - RPC name enumeration disabled")
    else()
        message(SEND_ERROR "Couldn't find an RPC program number database implementation!")
    endif()
```

**源码侧**（`src/network_inspectors/appid/service_plugins/service_rpc.cc`）：

```cpp
+#if !defined(SNORT_NO_RPC_DB)
    struct rpcent* rpc;
    RPCProgram* prog;
    ...                       // getrpcent() 枚举循环
    endrpcent();
    }
+#endif

    tcp_patterns =            // 其后的静态端口模式表原样保留
```

要点：

- **平台分支而非全局放行**：`elseif (CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")`
  只在 OHOS 上降级；其余平台行为逐字不变（非 OHOS 仍按上游 SEND_ERROR）。
- **STATUS 消息如实记录降级**：configure 日志可审计（不是静默丢功能），
  与「检测器语义降级但功能不丢」的取舍一并留痕。
- **静态端口模式即降级面**：`service_rpc` 的静态 `tcp_patterns` 表本就在
  枚举块之后无条件生效，宏只关掉动态数据库枚举。
- **宏名选择**：`SNORT_NO_RPC_DB` 为语义化否定宏（对照上游惯例，如
  `NO_STRNDUP` 类）；评审者从宏名可直读平台事实。

## 验证

- 探针（头文件/链接期探测/`/etc/rpc`）2026-10-03 真机实测，输出见上；
  libtirpc 可得性 2026-10-04 复测修正（`-r=ohpcd` → `libtirpc/1.3.7`）；
- snort 3.12.2.0 真机 `conan create`（ohos-aarch64 profile）：configure 输出
  `RPC program number database missing on HarmonyOS/OHOS - RPC name
  enumeration disabled`（STATUS，非 SEND_ERROR），构建/安装/测试全绿
  （CTest 158/158 + 消费者 E2E 6/6，完整数字见随 MR 的 notes.md）；
- 非 OHOS 平台：RPC 分支不进入，`SEND_ERROR`/`USE_TIRPC` 语义与上游一致
  （补丁其余 hunk——lzma 门控与 sh 包装——跨平台应用，行为等价）。

## 差异化定位与查重

| 最近邻 | 差异 |
|---|---|
| DRAFT-13904-swiftshader-musl-glibc-only-apis | 同族（musl 缺 glibc 扩展）。彼：编译期**声明**缺失（pthread_affinity/RTLD_DI_ORIGIN）→ 替换或 `#if __GLIBC__` 守卫。本条：**链接期符号 + 数据库文件**双缺失，且上游以其为 **configure 硬门**（SEND_ERROR）→ 修法是 CMake 平台分支降级 + 宏传播，不是单点守卫 |
| DRAFT-libnss_nis-3.4-glibc-nss-compat-headers | 同族（glibc 专有后端接口头缺失）；彼为 NSS 兼容头移植，本条为 RPC 数据库功能降级 |
| DRAFT-irpas-0.10-musl-errlist-registry-replace | 邻接点（共享 libtirpc 可得性事实）：彼在 registry 预编译替换中经 `-r=ohpcd` 取得 `libtirpc/1.3.7`（解决 `rpc/types.h` 缺头）；本条为 RPC 程序号数据库（configure 硬门 + `getrpcent` 枚举）缺失的降级修法——libtirpc 可得只解决"可编译"，本平台无 `/etc/rpc`，动态枚举运行期无数据 |
| DRAFT-E736 / DRAFT-E577（HarmonyOS cmake 平台模块） | 处理构建标志缺失；本条与之无交集（RPC 探测与平台模块无关） |

**查重记录**（2026-10-04 复核修正）：词边界检索 `tirpc` → 除本条目外零命中；
子串命中既有条目 5 份，已逐份核对——`DRAFT-irpas`（`-r=ohpcd` 取
`libtirpc/1.3.7` 的先例，见上表）、`DRAFT-libnss_nis-3.4`（rpc 模块仅用
`struct rpcent`，注明由 libtirpc 提供）、`DRAFT-ohos-shadow-job`（并发构建
环境噪声条目，将 libtirpc 等误判"依赖不可达"，非知识覆盖）；`getrpcent` /
`getrpcbyname` / `portmap` / `rpcbind` / `/etc/rpc` / "RPC program number"
→ 除本条目外零命中（2026-10-03 初检 + 2026-10-04 复核）。musl/glibc 族条目
逐一看过（argp/fcloseall/gcvt/dgettext/symver/errlist/NSS 等），无一覆盖
RPC 程序号数据库枚举 / configure 硬门场景。
