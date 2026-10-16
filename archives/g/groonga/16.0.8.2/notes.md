# Groonga 16.0.8.2 依赖修复

上游仍为 **16.0.8**；`.2` 是鸿蒙适配修复后缀（`.1` 已有他人待审 PR #11939，本次不覆盖）。原 `16.0.8` 归档和已发布制品保持只读。

PGroonga 的参数化分词器和规范化器依赖 Groonga 的 MessagePack 功能。原配方关闭了该功能，导致参数不能保存。本版本在 `source()` 下载并校验官方 **msgpack-c 6.1.0 C 源包**，放入 Groonga 上游读取的 `vendor/msgpack-c-6.1.0.tar.gz`；构建时明确选择 bundled、静态 PIC，并禁止缺少已校验源包时继续配置。

`msgpack-c` 是 Groonga 核心所需的 C 实现，与 PGroonga 自身使用的 `msgpack/7.0.1` C 库依赖分别处理。没有增加未发布的 Conan 依赖。

上游核心库的真实开关是 `GRN_EMBED`；它的静态嵌入模式不安装完整 CLI、头文件和数据。本配方提供完整共享库包，限定 `shared=True` 并设置 `GRN_EMBED=False`。保留原 RapidJSON 适配补丁、zlib/1.3.1.1 与 lz4/1.10.0 依赖。

## 验证方法与范围

真机为 HarmonyOS 6.1 PC aarch64，Clang 15.0.4、CMake 4.1.2、Conan 2.29。执行：

```sh
conan create . -pr:h=/path/to/ohos-native-profile -pr:b=/path/to/ohos-native-profile --build='groonga/*'
```

最终 **16.0.8.2** 已独立真机 `conan create` 验证，退出码 **0**；13 条 C API 断言及 **20/20** 原始用例通过。

消费者测试包括真实 C API（库函数调用）探针和 **20 个原始上游命令用例**，共 86 个命令响应。探针使用磁盘数据库创建带参数的 NormalizerNFKC130 / TokenNgram，检查对象及清理，13 条断言失败即返回非零。上游共有 4227 个 `.test` 文件，本轮只选定与参数化选项有关的 20 个；其余 4207 个未运行，不能声明全量通过。

原 `.test` / `.expected` 文件字节不变，逐文件 SHA256 由 inventory 核对。运行器只按官方 grntest 规则归一化外层成功响应的时间戳与耗时，业务结果逐字段匹配，类型、响应数、退出码和超时都严格校验。

OHOS 消费者只复制并重签本次临时副本，以满足设备对可执行文件/动态库的签名检查，不修改 Conan 缓存、关闭安全保护或改写原始测试。临时测试目录设置 `0770`，适配 HMDFS 文件系统行为。早期内存数据库探针在普通 table_create 即崩溃，不能作为 MessagePack 回归依据；改用官方 CLI 测试一致的磁盘数据库后实测正常。

共享 CI、制品仓 release 和维护者审核仍需独立通过。旧版历史 3373/4227 等结果不作为此版本验证数据。

## 官方依据

- [Groonga 固定版本 CMake](https://github.com/groonga/groonga/blob/v16.0.8/CMakeLists.txt)
- [核心库共享/嵌入模式](https://github.com/groonga/groonga/blob/v16.0.8/lib/CMakeLists.txt)
- [MessagePack C 6.1.0](https://github.com/msgpack/msgpack-c/releases/tag/c-6.1.0)


## 2026-10-15 官方同字节下载备选

共享CI#92221已获取Groonga和msgpack源码，但Onigmo官方release下载连接超时。保留原canonical URL及SHA256，正常下载失败时通过官方GitHub API仓库k-takata/Onigmo、asset10846880获取同一844935字节资产，Accept:application/octet-stream及显式tar.gz文件名，仍校验原SHA256 c648496b5339953b925ebf44b8de356feda8d3428fa07dc1db95bfe2570feb76。两种传输声明校验值不一致立即失败；原始下载hash失败不回退，API校验/网络失败也返回失败。

CI预下载逐字扫描YAML的HTTP地址且不转发Accept头，把API直接写成URL会错误缓存JSON。因而conandata用显式repository/asset_id结构声明API传输，再由source()构造官方端点；未修改共享CI、引入镜像或减弱校验。

macOS下真实Conan2.33和2.29.1分别验证正常下载故障→API、两个端点皆坏、API内容坏、canonical校验坏，以及原样CI镜像/预下载curl存在和缺失两路径。成功源树均11753文件逐项SHA256与原基线一致；损坏场景退出1，canonical损坏不请求API。改动仅下载路径，build/package/test代码及测试字节不变。此前完整鸿蒙原生conan create、消费者13条、所选上游20/20属于1618fc05时的构建记录；新下载路径尚待本提交的目标CI验证，不将本地源码验证写成新head目标构建通过。


## 2026-10-15 JSONPath依赖源码提前校验

#92808已越过Onigmo源码阶段，随后上游CMake FetchContent直接下载jsoncons1.7.0失败。本提交将同一官方归档提前纳入source()并保存为上游原生识别的vendor/jsoncons-1.7.0.tar.gz；版本与SHA256 5a2aad4e791a1c93b0b0b326973459753a96a4c48d06d3035cd0ea0d262198d4均取自Groonga16.0.8官方CMake。没有关闭JSONPath或修改上游CMake/测试，也不再依赖CMake配置时联网。

真实Conan2.29.1源码阶段退出0，损坏归档SHA校验失败退出1；11753个原有输入逐文件不变，仅新增同校验值vendor归档。macOS禁网沙箱内使用逐字原上游JSONCONS及FetchContent块，配置、编译、JSONPath消费者全部退出0，输出[1,2]且无file(DOWNLOAD)调用。该局部离线验证不代表完整Groonga或OHOS新head构建通过，仍待新CI。缺归档本地诊断因CMake长重试被终止，标为无结论；实际#92808原始错误是本次失败基线。
