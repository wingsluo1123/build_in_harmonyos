# minicsv ec11134f7f 适配笔记

MiniCSV 是单文件、无堆分配的 CSV 解析 C 库（BSD/ISC 许可），上游无 tag，
任务版本标识 `ec11134f7f` 对应上游 master HEAD commit
`ec11134f7f0b01b7981d5568bc4a9c85b00a21e8`（ls-remote 核验）。

## 编译环境
- 构建系统: 无上游构建系统（单文件库），配方内注入最小 CMakeLists.txt
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（OHOS aarch64 工具链，aarch64-linux-ohos）
- Conan profile: ci/conan/profiles/ohos-aarch64
- 状态: built（本地 W3 通过；远端 CI/制品仓发布由合并后流水线完成）

## 编译步骤

1. 上游源码核验：`git ls-remote https://github.com/jedisct1/minicsv`，
   master HEAD = ec11134f7f0b01b7981d5568bc4a9c85b00a21e8（无 release tag）。
2. 官方 GitHub archive 下载，SHA-256 =
   35a1370df1a32c9bb62d619ed625d8688b84c784fe57c352f1b89891b2d4800a。
3. 探索性编译（clang -fPIC -O2）：minicsv.o + llvm-ar 静态库，
   上游 minicsv-test.c 编译并运行 rc=0。
4. lang-preflight：detected_language=c（c↔cpp 兼容族），通过。
5. 写入 conanfile.py（注入最小 CMakeLists.txt）+ conandata.yml + test_package/。
6. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`：
   构建 libminicsv.a + 安装 minicsv.h，test_package 1/1 通过，rc=0。
   注：首次运行时 github.com 下载超时（网络抖动），将本地已核验 tarball
   预置进 conan 下载缓存后重跑成功；此属本机缓存预置，不影响配方本身。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create source() 下载 github.com 超时 | 网络抖动/连接超时 | 将本地已核验 tarball 按 conan 下载缓存键预置进 ~/.conan2/dl/s，重跑成功 |
| 2 | test_package ctest 首次失败 expected 8 cols got 9 | test.c 断言列数写错（row2 实际 9 列） | 修正断言为 9，重跑 conan create 通过 |

## 源码修改

无补丁（patches/ 为空）。配方在 build() 内注入最小 CMakeLists.txt
（add_library(minicsv minicsv.c) + install），与 MurmurHash3 配方同模式。

## 依赖版本

无第三方编译/运行依赖。

## 验证结果

- 上游测试：`clang -O2 -I. minicsv-test.c libminicsv.a -o minicsv-test && ./minicsv-test` → rc=0
- conan create（OHOS aarch64 profile）：rc=0，test_package 1/1 通过
- 鸿蒙特有测试（reports/harmonyos-test.c，链接打包产物）：
  运行 2 次均 rc=0、PASS（0 failures），__OHOS__=1、HongMeng Kernel 1.12.0 aarch64，
  12 项断言全过（转义引号、多行单元格、空列、trim）。
  日志 SHA-256：a4077b083df9e2384984bb69fe978b932cb9e016026db9a7ac41eb60c8fb6d93
  （run1/run2 输出一致）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（注入最小 CMakeLists.txt） |
| conandata.yml | 官方源码 URL + SHA-256 |
| test_package/ | CMakeLists.txt + test.c（消费者视角断言）+ conanfile.py + MANIFEST.yml |
| reports/harmonyos-test.c/.bin/.log | 鸿蒙特有测试源码、二进制、运行日志 |
| manifest.yaml / notes.md | 元数据与适配笔记 |

## 注意事项

- 上游无 tag；版本标识 ec11134f7f 即上游 master HEAD commit，已核验。
- 库为纯 C、无堆分配、无平台特定代码，OHOS 适配零改动（R40 无平台 stub 需求）。
---

**编译结束**: 2026-09-28 23:16
**最终状态**: built
