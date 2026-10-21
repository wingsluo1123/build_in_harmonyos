# ECOS

ECOS 是 embotech 发布的嵌入式凸锥优化求解器，支持线性、二阶锥、指数锥与 Boolean 分支定界。

上游： https://github.com/embotech/ecos

## 2.0.10

本目录提供 Conan 2 配方及 6 个补丁，默认静态库、长索引；支持 shared/use_long 选项。
补丁处理 CMake 安装和测试注册、ARM unsigned char 下的负值节点状态、上游 BB 测试预期与指数锥用例精度。
消费者使用 `find_package(ecos CONFIG REQUIRED)` 和 `ecos::ecos`；许可证与第三方许可随包保留。

正常启用 C 套件 38 项和公共 API 消费者 20 项已有 Windows/OHOS7 AArch64 QEMU 直接证据。
完整本地 W3 已通过；正式 Conan 验证、官方远端 CI 和评审状态以版本目录 notes.md 和实际回执为准。
MATLAB/CVX/MEX/UFget、Python2/QCML 及两项上游未启用 C 入口不计入 38 项通过统计。
