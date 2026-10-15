# crypto-algorithms cfbde48414 适配笔记

## 编译环境
- 构建系统: none（纯 C .c/.h 源码集合，无 configure/Makefile/CMake）
- 版本标识: 上游 commit cfbde48414baacf51fc7c74f275190881f037d32（2015-04-27，GitHub 官方 archive tarball）
- 编译日期: 2026-09-26
- 编译器: clang 15 / clang++（OHOS aarch64 profile）
- 状态: published

## 编译步骤
库为无构建系统的源码集合（README: "Compiling them should be as easy as adding the relevant source code to the project"），
每个算法是独立的 .c/.h 对（aes/arcfour/base64/blowfish/des/md2/md5/rot-13/sha1/sha256），并有配套 *_test.c known-answer 自检程序。

Conan 配方（header-only 变体）：
1. source(): get() 从官方 archive tarball 下载并 strip_root
2. build(): 无编译产物——用工具链编译器逐个编译并运行全部 10 个上游 *_test.c（R51 上游测试三步法，HMBS_UPSTREAM_TEST_RESULT）
3. package(): 重分发 *.h 与算法源 *.c 到 include/（消费方自行编译所需 .c，符合上游用法）；不打包 *_test.c
4. package_info(): cpp_info.includedirs=include，无预编译库；cmake_file_name=crypto-algorithms
5. package_id(): clear()——无 os/compiler 依赖，单一 package_id

test_package: CMake 消费者测试，通过 find_file 定位打包的 sha256.c，连同 test.c（SHA-256("abc") known-answer 校验）一起编译并运行（R34 真实 API 调用）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 github.com 下载超时 | 本机访问 github.com 443 被网络策略阻断（api.github.com / codeload.github.com 可达） | 手动从 codeload.github.com 下载 commit tarball 到 ~/tmp/builds，再跑 init-build 复用；sha256 与官方 archive URL 一致 |
| 2 | conan-init 默认生成 autotools 模板 | 模板按 URL 猜测构建系统，未识别无构建系统库 | 按 header-only / 无构建打包族模板（v12.21）重写配方；build() 用上游测试验证而非伪造编译日志 |

## 源码修改
无（0 patch，`patches: {}`）。上游是纯标准 C（stdio/string/memory），无平台相关代码，无需 OHOS 适配改动。

## 依赖版本
无（0 依赖，`requirements()` 为空）。

## 验证结果
```bash
# 上游 10 个 known-answer 测试（Adapt 阶段本机编译运行）
aes/arcfour/base64/blowfish/des/md2/md5/rot-13/sha1/sha256: 全 SUCCEEDED/PASSED
# conan-verify / finish（OHOS aarch64 profile）见 conan create 日志与 .ci-result.json
```

## 注意事项
- 该库明确声明 NOT cryptographically secure（无侧信道防护），仅适合教育/测试向量用途——配方 description 与许可证如实标注 public domain。
- 消费方需自行编译所需算法 .c 源：这是上游设计，非本配方缺陷。
---

**编译结束**: 2026-09-26 21:52
**最终状态**: built
