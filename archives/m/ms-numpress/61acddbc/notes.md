# ms-numpress 61acddbc 适配笔记

## 编译环境
- 构建系统: custom（无顶层 configure/CMake/Makefile，C++ 主体直接编译）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++（ohos-sdk_26.0.0.18）
- 状态: built

## 编译步骤

1. init-build 引导：官方 archive 下载（commit 61acddbc）
2. lang-preflight：仓库为跨语言算法库（C++ 主体 src/main/cpp），Java/C#/Python/R
   为语言移植；语言移植目录内的 setup.py 属绑定/辅助脚本，按 D.4 规则不计主体
3. 上游测试实测：`clang++ -std=c++11 MSNumpress.cpp MSNumpressTest.cpp -o test && ./test`
   → all tests succeeded（encodeLinear/decodeLinear、encodePic/decodePic、
   encodeSlof/decodeSlof 全部通过）
4. conan-init 生成配方 → 修正为 custom 直接编译（原 autotools 模板不适用）
5. conan-verify：G1-G5 全部 PASS（G2 conan create 干净构建 + test_package 往返测试）
6. finish：W2 结构完整（conanfile.py/conandata.yml/test_package/MANIFEST.yml 齐全）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 将 git 仓库 URL 当 tarball 下载返回 HTML | GitHub 仓库页非 archive tarball | 改用官方 archive URL（/archive/<commit>.tar.gz）并核验 commit 存在 |
| 2 | conan-init 误用 autotools 模板 | 构建系统探测为 autotools | 改写 conanfile.py 为 custom 直接编译 MSNumpress.cpp |
| 3 | test_package 空壳测试（仅 print） | 模板默认 test.c | 改写为真实调用 encodeLinear/decodeLinear、encodePic/decodePic 并验证往返误差 |
| 4 | decode 调用签名错误 | 误传 4 参数（上游 decode 为 3 参数） | 按上游 MSNumpress.hpp 签名修正 |
| 5 | PIC 往返误差断言失败 | 测试用小 double 超出 PIC 有损编码容差 | 按上游 encodeDecodePic 口径改用 rand()%1000000 大整数，误差 < 0.5 |

## 源码修改

无（无补丁，patches/ 为空；配方层完成适配）

## 依赖版本

无第三方依赖（仅标准库 <cstddef>/<vector>/<iostream>/<cmath>/<climits>/<algorithm>）

## 验证结果

```bash
# 上游测试（src/main/cpp 下）
clang++ -std=c++11 -O2 MSNumpress.cpp MSNumpressTest.cpp -o test && ./test
# → all tests succeeded!

# conan create（ohos-aarch64 profile）
conan create archives/m/ms-numpress/61acddbc -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → test_package 全部断言通过，G2-G5 PASS
```

## 注意事项

- 归档 conandata.yml 必须保持官方纯 URL（R39/PF7），本地 CI 模拟的镜像注入
  （ghfast.top）已恢复原样，无 .orig/.ghfast-bak 残留
- 该库在 HarmonyOS PC（OHOS/aarch64）下直接以 clang 编译，无平台宏需求
---

**编译结束**: 2026-09-28 23:30
**最终状态**: built
