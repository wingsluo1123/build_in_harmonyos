# paho.mqtt.c 1.3.16 HarmonyOS PC 适配笔记

## 范围

- 上游版本：1.3.16，源码归档 SHA256：8b960f51edc7e03507637d987882bc486d8f4be6e79431bf99e2763344fd14c5。
- HarmonyOS PC / AArch64；构建 MQTT 同步与异步静态库，并验证静态库可用于共享库链接。
- with_ssl 默认关闭；开启时使用 OpenSSL 3.5.8.1 并构建 Paho SSL 库。
- 此处 SSL 指 Paho 的 OpenSSL 加密传输；设备测试验证 TLS 1.2 与 TLS 1.3，不启用 SSLv3。

## HarmonyOS 源码适配

OpenSSL 构建下，src/SSLSocket.c 原本在包含 Heap.h 后才间接包含 POSIX 线程头。Paho 的堆跟踪宏会将 free 重定义为 myfree，导致 HarmonyOS SDK 的 pthread.h 所引入的 sched.h 中 free(void *) 声明被宏展开，编译失败。补丁在 Heap.h 之前显式包含 pthread.h，让系统声明先完成解析；Windows 不受影响。知识条目：E429（草稿，待知识库审核）。

## 发现与知识

- ✅ E429 已沉淀为知识草稿并由 manifest.yaml 的 knowledge_ref 引用：开启 OpenSSL 时，HarmonyOS 的 pthread/sched 头文件需在 Paho Heap.h 堆跟踪宏之前包含；草稿文件为 knowledge/drafts/E429-draft-F7D9.kv 与 .md，等待知识库审核合入。

## 验证结果

- Windows 本地 Conan create 使用 HarmonyOS 6.0 / AArch64 / Clang 15 profile。默认和 TLS 包均构建成功；两种配置的 test_package 测试程序与共享链接探针均交叉编译成功。Conan test() 因宿主不能运行 OHOS AArch64 程序而跳过运行。
- 本次 Conan 与真机验证使用默认 `shared=False` 静态包；配方提供 `shared=True` 选项，但该共享库包变体未在本轮构建或真机测试。
- 将相同 test_package 测试源编入 signed HAP，并让 HAP 直接链接对应的当前 Conan 包静态库后，在 HarmonyOS 6.0 真机通过无线 HDC 运行。共有 4 个不同测试项：HarmonyOS 平台探测、普通 MQTT 往返、TLS 1.2、TLS 1.3，均通过。默认配置执行 2/2 项，TLS 配置执行 4/4 项；两配置合计 6 次场景执行，其中平台探测和普通 MQTT 各重复一次。
- 上游源码清点：`test/` 树含 25 个 C 源文件和 9 个 Python 脚本。静态 + SSL 的 CTest 清单登记 127 项（99 个非 WebSocket、28 个 WebSocket）；静态+共享+SSL 完整清单登记 279 项：静态 127 项、共享 152 项（99 个非 WebSocket、53 个 WebSocket）。277 项与本轮完整清单相差两个 `test_connect_destroy-1-execute-destroy-during-connect` 注册项：静态链接 #278 和共享链接 #279；session-present 的 #276/#277 已计入 277。两种 connect-destroy 注册项均在对应非 WebSocket 真机运行中通过。279 项中，263 项有直接 CTest Passed 记录；另 16 项为 8 个 MQTT v5 场景（test10-2/3/5/6、test11-2/3、test45-1/4）分别使用静态和共享链接配置运行上游协议驱动，16 项均输出通过且 0 failures。非 WebSocket 首轮为 82 项通过、17 项失败；失败项在修正证书链与 MQTT v5 协议夹具后均通过定向复测。WebSocket 首批出现失败/中断；修复 `LWS_WITH_EXTERNAL_POLL` broker 和 `mqttsas.py` 的 MQTT/TCP 1882 后端、TLS/WebSocket 测试夹具后，原失败/中断项及先前未启动项均有通过证据。现有证据覆盖完整清单 279 个测试项的成功执行，但不是单次全量 279 项复跑。逐项日志保存在设备临时目录 `/storage/Users/currentUser/tmp/paho-upstream-ctest-20261016`（清单 `ctest-list-full.log`、静态及共享 CTest 首轮/复测日志、TLS/WebSocket 夹具日志和 16 个 MQTT v5 定向运行日志），没有把原始日志放进归档。mTLS WebSocket 使用临时 Python TLS/WebSocket 桥接，因为设备 Mosquitto/libwebsockets listener 在 TLS 验证后未返回 HTTP 101；桥接用例验证 Paho 的 mTLS/WSS 客户端链路，不覆盖该 Mosquitto listener。
- TLS 自签名回环测试关闭 CA 验证，仅确认协议协商和数据路径，不覆盖公共 CA 与外部 MQTT 服务。
- 此前 Windows 原生环境的 `finish` 未完成：G0 找不到原始源码 tarball，G2 的 POSIX shell 命令无法在 Windows 命令环境执行，W3 又被仓库级检查阻断。2026-10-16 已在 HarmonyOS 真机重新执行：Conan G2/G3 与 W3 通过，设备生成的 `.ci-result.json` 与 W3 日志哈希一致；后续发布打包和 submit 就绪检查仍缺少产物，详见测试报告。

## Conan 用法

默认构建不引入 OpenSSL。TLS 构建需将 paho.mqtt.c 与 test_package 的 with_ssl 同时设为 True，并使用 openssl/3.5.8.1 静态依赖。HarmonyOS 目标可交叉编译；设备运行验证通过 HAP 在实际 HarmonyOS 设备执行。

---

验证结束：2026-10-16（UTC+08:00）
最终状态：built；HarmonyOS 真机 Conan G2、G3 与 W3 通过；finish 的发布打包与 submit 就绪检查仍有缺项；静态+共享+SSL CTest 清单登记 279 项，当前每项均至少有一次 PASS 证据（静态 127、共享 152）；未执行单次全量复跑。另有 4 个不同的 Conan/HAP 设备测试项通过。
---

**编译结束**: 2026-10-16 00:49
**最终状态**: built

### 对话 #1：HarmonyOS 真机 finish 与 W3 验证（2026-10-16）

- 在 HarmonyOS 6.0/AArch64 设备 `10.53.45.8` 上执行 finish；Conan G2/G3 和 W3 通过，test_package 实际运行 MQTT 与网络/TLS 集成场景。上游静态 + SSL CTest 登记 127 个测试项；首轮及夹具修正后的执行留下 17 个非 WebSocket 失败项、9 个 WebSocket 失败项和 2 个中断项。收尾定向复测中，这 28 项全部通过；连同此前成功项，127 个 CTest 测试项现均有成功结果。没有执行单次全量复跑。
- `.ci-result.json` 由设备端 finish 自动生成，exit_code=0，其日志 SHA256 与本地 W3 日志一致。
- finish 的归档发布打包/submit 就绪项仍缺 packaging 产物与 `.staging-verified`；没有把缺失项伪报为通过。原始设备和上游测试日志保存在本地验证工作区，不随归档包提交。
