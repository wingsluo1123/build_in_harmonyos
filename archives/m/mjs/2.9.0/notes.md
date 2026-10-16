# mjs 2.9.0 适配笔记

## 编译环境
- 构建系统: makefile（单文件 amalgamated：mjs.c/mjs.h，直接 clang 编译 + ar/ranlib 归档）
- 编译日期: 2026-09-28
- 编译器: clang（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang，triplet aarch64-linux-ohos）
- 状态: built

## 编译步骤

1. `conan create archives/m/mjs/2.9.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. 配方直接编译 `mjs.c` 为 `libmjs.a`（`-fPIC -O2`），`ar rcs` + `ranlib`
3. test_package 消费者测试（CMake + mjs::mjs 目标）验证 create/exec/数值/布尔/字符串 API

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 上 `(0-14) >>> 2` 得 0（期望 1073741820）、`mjs_get_int(-14)` 错读 | 负数 double 直接强转 uint32/int32 是 C 标准 UB；x86 恰好按位回绕，aarch64 饱和为 0 | 补丁 0001-fix-int32-aarch64-ub.patch：先转 int64_t 再收窄（`(uint32_t)(int64_t)` / `(int)(uint32_t)(int64_t)`） |
| 2 | 上游单测缺 `common/test_main.h`（release tarball 未含） | 上游 tarball 不含 common/test_main.h | 本地 harness 补全（仅本地验证用，不交付）；42 tests / 3436 checks 全过 |
| 3 | test_package 初版使用私有 API（MJS_TAG_UNDEFINED、mjs_is_truthy、mjs_json_stringify、mjs_gc、mjs->owned_values） | 打包头文件只暴露公开 API，struct mjs 不透明 | 重写 test_mjs.c 仅用公开 API（mjs_mk_undefined/mjs_get_bool/mjs_sprintf） |

## 源码修改

- `patches/0001-fix-int32-aarch64-ub.patch`：TOK_URSHIFT 与 mjs_get_int 两处 double→int32 转换 UB 修复（经 int64_t 中转）

## 依赖版本

- 无外部运行时依赖（requirements 为空）；链接 `-lm -ldl`

## 验证结果

```bash
# 上游单测（本地 harness，42 tests / 3436 checks）
cd <src> && unit_test_v2   # All tests passed: 42 tests, 3436 checks
# test_package 消费者测试（OHOS aarch64）
./test_mjs                 # mjs consumer test passed
# W3 本地 CI 模拟
build_and_test.sh archives/m/mjs/2.9.0   # PASS（.ci-result.json exit_code=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 单文件 C 库配方（static libmjs.a） |
| conandata.yml | 官方 GitHub tarball（sha256 b7b331f…）+ 补丁声明 |
| patches/0001-fix-int32-aarch64-ub.patch | aarch64 负数 double 转换 UB 修复 |
| test_package/ | 消费者集成测试（公开 API，验证 aarch64 修复） |

## 注意事项

- mjs 为 GPL-2.0-only 库，配方已声明 license
- 知识沉淀：aarch64 负数 double→int32 转换 UB 的跨库可复用模式见 `knowledge/drafts/DRAFT-mjs-2.9.0-aarch64-double-int32-conversion-ub.*`