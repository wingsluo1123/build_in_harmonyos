# E429 — Paho OpenSSL 编译时 HarmonyOS pthread 声明被堆跟踪宏改写

## 错误特征
打开 Paho 的 PAHO_WITH_SSL 后，HarmonyOS AArch64 SDK 在编译 src/SSLSocket.c 时于 sched.h 的 free(void *) 原型附近报告 “expected parameter declarator”。普通非 SSL 构建不触发。

## 触发条件
- 构建系统: CMake / Conan
- 阶段: C 编译
- 平台: HarmonyOS PC AArch64，OpenSSL 支持开启

## 根因分析
SSLSocket.c 在 POSIX 平台先包含 Heap.h，后续 SocketBuffer.h 间接包含 Socket.h、Thread.h 和 pthread.h。Heap.h 的堆调试宏将 free(x) 改写成 myfree(__FILE__, __LINE__, x)，HarmonyOS pthread 头链中的 sched.h 随后声明 free(void *) 时也被该宏展开，破坏函数原型。此问题发生在 Paho 1.3.16 的 OpenSSL 代码路径，不影响关闭 SSL 的构建。

## 解决方案

### 推荐方案
在 OPENSSL 条件分支中、Heap.h 之前显式包含 pthread.h，并仅对非 Windows 编译生效。这样系统头文件先完成解析，再定义 Paho 的 free 跟踪宏；配方通过正式 portability patch 分发。

### 禁止做法
- ❌ 不要通过定义 __OHOS__ 或替换 allocator 宏绕过编译；这会隐藏系统头文件顺序问题，并可能改变非 SSL 或其他平台的内存行为。
- ❌ 不要仅因无 SSL 构建通过就认定 TLS 适配完成。

## 验证
```bash
conan create archives/p/paho.mqtt.c/1.3.16 -pr:h=<HarmonyOS-AArch64-profile> -o 'paho.mqtt.c/*:with_ssl=True' -o 'paho.mqtt.c/*:shared=False' -o '&:with_ssl=True'
```

在 HarmonyOS 6.0 设备运行 test_package，确认 `uname()` 返回 HongMeng 标识，plain MQTT 往返成功，并分别观察 Paho `ssl://` 会话协商 TLSv1.2、TLSv1.3 后完成 CONNECT/PUBLISH/DISCONNECT。

## 关联条目
- 相关: 暂无；这是当前 Paho OpenSSL 路径实测得到的 HarmonyOS 头文件顺序问题。
