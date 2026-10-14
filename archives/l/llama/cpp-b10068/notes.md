# llama.cpp cpp-b10068 适配笔记

## 版本身份

- 上游:https://github.com/ggml-org/llama.cpp,tag `b10068`
- tag 对应 commit:`571d0d540df04f25298d0e159e520d9fc62ed121`(2026-07-18)
- 源码 tarball:codeload 官方 URL,sha256 已在 Windows 端对官方 tarball 计算并写入 conandata.yml
- 注:tag 命名沿用上游 build 号格式(`b<build-number>`),平台任务版本字段为 `cpp-b10068`

## W0 依赖分析(Windows 阶段,2026-10-12)

**必需依赖:无**(全部第三方库 vendor 在源码树内):

| vendor 目录 | 用途 |
|---|---|
| vendor/cpp-httplib | llama-server HTTP 栈(OpenSSL 可选) |
| vendor/nlohmann | JSON |
| vendor/miniaudio | tts 工具音频 |
| vendor/stb | 图像处理 |

**可选依赖(默认关闭)**:
- OpenSSL(`LLAMA_OPENSSL=OFF`):仅 server HTTPS 需要,关闭后零外部依赖,无 L0j 依赖风险
- OpenMP(ggml `GGML_OPENMP`,默认 OFF)
- LibreSSL/BoringSSL(`LLAMA_BUILD_LIBRESSL/BORINGSSL`):默认 OFF 的 FetchContent 项,不得开启(会构建期联网)

**构建系统**:CMake,超项目同时构建 ggml(ggml-base/ggml-cpu/ggml)+ libllama + libllama-common + tools(cli/server/quantize/llama-bench 等)+ app(统一二进制)。

## 关键 OHOS 适配点

1. **GGML_NATIVE=OFF**(必改):上游默认 `-mcpu=native` 探测(check_cxx_source_runs),把构建机 CPU 特性烧进产物。关闭后经 `GGML_CPU_ARM_ARCH` 指定,或留编译器基线(armv8-a)。知识先例:fasttextembed 1.0.2 native-cpu-flag-gate、ascon-c 1.3.0 REL_FLAGS。
2. **SONAME + 重签名**:产物 .so 无 DT_SONAME,`package()` 内 patchelf 补 SONAME 并重签名(patchelf → llvm-objcopy 剥 .codesign → binary-sign-tool selfSign,顺序不可换)。ggml 0.17.0.1 同款,覆盖 5 个 .so。
3. **WebUI 离线化**:`LLAMA_USE_PREBUILT_UI=OFF` 禁止构建期从 huggingface.co 下载 dist.tar.gz;上游脚本降级为内嵌空 UI(仅 WARNING,不 FATAL_ERROR)。
4. **警告旗标**:`GGML_ALL_WARNINGS=OFF`,防 split C/C++ 编译器 profile 混入 Clang 专属旗标(ggml 0.17.0.1 同款)。
5. 共享库与工具并存:非系统同名库(llama/ggml 均不在 /lib 系统集),R26 不适用,默认 shared=True。

## 上游测试计划(MateBook 执行)

- 构建:`LLAMA_BUILD_TESTS=ON` 后 ctest 套件全部可编译。
- **离线可跑**:tokenizer-0/1 系列(所需 `models/ggml-vocab-*.gguf` 约 60MB 已提交在源码树)、test-sampling、test-grammar-*、test-quantize-*、test-chat、test-json-schema-to-grammar、test-batch-alloc、test-llama-grammar 等。
- **需模型文件**:test-recurrent-state-rollback 等经 `get-model.cpp` 读 `LLAMACPP_TEST_MODELFILE`,未设则优雅跳过(exit 0 + WARNING)——以跳过如实计数,或提供小模型。
- **需联网**:`test-download-model` 单项 ctest 从 HF 下载,离线排除并说明。
- 通过率口径:≥90%(路径 C 要求),逐项列表如实报告。

## test_package(消费者用例)

- 编译链接 `llama::llama`(CMakeDeps),调用公开 API:`ggml_version()` + `llama_max_devices()`,校验非零返回。
- 交叉构建时仅做编译链接验证(ggml 0.17.0.1 同款)。

## Windows 阶段已完成

- [x] 平台任务核对(用户已认领 contrib-8511;分支名/sourceUrl 以任务页为准,交接前逐字核对)
- [x] W0 依赖分析(见上)
- [x] W0b 知识核验(fasttextembed/ascon/soname/E452 重签;无 llama 专属草稿)
- [x] 查重:archives 无 llama;平台全量 13708 任务无 llama 认领/完成记录;ggml 0.17.0/0.17.0.1 为独立任务不冲突
- [x] 官方 tarball sha256 计算
- [x] 配方、conandata、test_package、commands.json、manifest、README 撰写

## 留给 MateBook 的验证项

1. L0j:`conan list -r=ohpcd` 确认制品仓无 `llama/cpp-b10068`(Windows 无法查 registry)。
2. `conan create` 全量构建(预期 30-60 分钟,tools 全开)。
3. ctest 上游测试(离线子集全跑 + 逐项记录跳过/失败)。
4. `conan test` 消费者用例。
5. `ohc-run.py finish llama cpp-b10068 built` → `.ci-result.json`。
6. W4 审计:`pre_pr_audit.py generate` → 独立审计子任务 → `report` → P0/P1 清零。
7. 审计若报 manifest 纯文档类项,按现行规则处理;`.ci-result.json`/审计结果不进 git。
