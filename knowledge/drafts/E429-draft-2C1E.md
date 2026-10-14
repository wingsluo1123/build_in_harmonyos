# E429 — Align OpenSSL ABI across reused Conan binaries and source-built dependencies

## 基本信息

- 严重度：2（中）
- 类别：conan、dependency、linking、runtime
- 来源：Janus 1.4.1 HarmonyOS PC AArch64 移植
- 状态：草稿；尚未进入正式知识索引

## 错误特征

Conan 依赖图同时复用一个已发布二进制包，并从源码构建另一个 TLS 依赖；前者的构建记录绑定 OpenSSL 1.1.x，后者配方默认选择 OpenSSL 3.x。风险可从 Conan 版本冲突信息或配方/制品元数据中的 OpenSSL 版本对发现，也可能在错误图下表现为链接缺符号或运行期符号加载问题。

Janus 1.4.1 适配时，HarmonyOS 的 libnice 0.1.21 制品使用 OpenSSL 1.1.1w，而 libwebsockets 4.3.5.1 配方默认要求 OpenSSL 3.5.6。本次在最终构建前通过制品和配方元数据发现并消除了版本分歧；没有故意构建错误 ABI 组合来制造运行失败。

## 触发条件

- Conan 应用依赖图复用已编译的传递依赖。
- 同一应用还要从源码构建使用 OpenSSL 的依赖。
- 二进制制品的 OpenSSL ABI 与源码依赖配方的默认 OpenSSL 版本不同。

## 根因分析

Conan 的根依赖 override 会影响依赖图的版本选择，但不会重新编译已发布的二进制制品。若只把图中的 OpenSSL 版本改成另一个版本，却继续复用按旧 ABI 编译的二进制，依赖图的表面一致不能证明二进制兼容。反过来，保留二进制 ABI、但让新源码依赖按另一个 OpenSSL 版本构建，也会让同一个服务进程承载未经验证的 ABI 组合。

## 解决方案

### 推荐方案

1. 查阅已复用制品的配方、manifest 或构建记录，确认它实际绑定的 OpenSSL 版本。
2. 在消费端 Conan 配方显式将根图统一到该版本。
3. 对默认要求不同版本的源码依赖从源码构建，使其使用被选中的 OpenSSL。
4. 检查最终 Conan 图确实只选择预期版本，并在目标设备上运行消费端集成测试。

Janus 1.4.1 的做法是在根配方中声明 self.requires("openssl/1.1.1w", override=True)，并从源码构建 libwebsockets 4.3.5.1。

### 回退方案

如果产品必须使用较新的 OpenSSL，应从源码重建所有绑定旧 ABI 的二进制依赖及其受影响消费者，并用同一目标 profile 验证完整闭包。不要仅改 Conan override 或元数据来伪装已有二进制的 ABI。

### 禁止做法

- 不要把 OpenSSL override 当作二进制依赖的重编译。
- 不要仅凭 Conan 图成功解析就认定跨版本 ABI 组合安全。
- 不要隐藏制品实际使用的 OpenSSL 版本或伪造 package metadata。

## 验证

Janus 1.4.1 在 HarmonyOS PC 6.0 AArch64 上统一到 OpenSSL 1.1.1w；最终 Conan create 成功。设备上的消费者测试启动打包后的 Janus，完成 REST session 与 EchoTest 生命周期，并完成 WebSocket RFC 6455 握手和 Janus info 请求。完整命令和包修订记录见 archives/j/janus/1.4.1/notes.md。

## 查重说明

已检索现有知识索引。E412 覆盖显式可选 OpenSSL 后端依赖，E509 覆盖动态加载器查找 OpenSSL；两者没有覆盖“复用绑定旧 OpenSSL ABI 的二进制，同时源码构建 sibling 依赖并统一 Conan 根图”这一边界，故本条作为补充草稿。

## 适用范围

适用于 Conan 应用依赖图中复用已发布二进制并混合构建 TLS/OpenSSL 依赖的场景。版本号仅用于 Janus 案例，不限定后续软件或 OpenSSL 版本。