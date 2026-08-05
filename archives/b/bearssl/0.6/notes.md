# bearssl 0.6 适配笔记

## 编译环境
- 构建系统: custom Makefile (conf/Ohos.mk)
- 编译日期: 2026-04-24 (Conan 适配: 2026-08-05)
- 编译器: clang
- 状态: published（Conan 配方验证通过）

## 编译步骤
1. 创建 conf/Ohos.mk 配置文件（CC=clang, LD=clang, LDDLL=clang）
2. `make CONF=Ohos lib` 编译静态库
3. `make CONF=Ohos tools` 编译 brssl 工具
4. `make CONF=Ohos tests` 编译测试程序
5. 手动复制头文件和静态库到 staging 目录

## Conan 适配
- 构建系统: 自定义 Makefile（非 autotools/cmake）
- conanfile.py: generate() 创建 conf/Ohos.mk, build() 调用 make CONF=Ohos lib
- conandata.yml: 官方源 https://www.bearssl.org/bearssl-0.6.tar.gz
- test_package: SHA-256("abc") 验证测试（调用 br_sha256_* API）
- conan create: PASS (test_package 1/1 passed)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无标准 configure/make install | BearSSL 使用自定义构建系统 | 创建 conf/Ohos.mk + conanfile.py generate() |
| 2 | AES_x86ni/AES_pwr4 不可用 | ARM 平台不支持 x86/POWER 指令 | 预期行为，使用通用 C 实现（autodetection） |
| 3 | Conan copy() 不复制 .a 文件 | src 参数需为目录非文件 | 使用 os.path.join(source, "ohos") 而非完整路径 |

## 验证结果
- testcrypto all ✅（所有加密算法测试通过）
- testx509 ✅（18 个证书验证测试通过）
- brssl impl ✅（平台检测正确: BR_64=1, BR_CLANG=1, BR_AES_X86NI=0）
- conan create test_package ✅（SHA-256 验证通过）

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| bearssl-0.6-ohos-aarch64.tar.gz | 1.5MB | 预编译包 |

---

**编译结束**: 2026-08-06 00:12
**最终状态**: published
