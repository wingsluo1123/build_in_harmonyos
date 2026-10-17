# DRAFT-apt-pkg-2.7.14-ohos-sdk-probe-dual-layout

> Contributor: gcw_eQ4VpLdf | Status: Draft | Updated: 2026-10-11
> Source: apt-pkg 2.7.14 HarmonyOS PC 适配（PR #14901, CI #80045）
> 领域：conan / ohos / sdk-detection / cross-compile

## 背景

apt-pkg 2.7.14 在 HarmonyOS PC（aarch64-linux-ohos）适配中,`conan create` 在 CI worker
上于 `generate()` 阶段失败：`Invalid configuration: OHOS native SDK (libcxx-ohos headers)
not found`。本地开发机构建却是全绿的——典型的「本地绿 ≠ CI 绿」跨环境差异。

## 错误签名

```text
ERROR: apt-pkg/2.7.14: Invalid configuration: OHOS native SDK (libcxx-ohos headers) not found;
set OHOS_NATIVE_SDK/OHOS_SDK_ROOT or install the SDK (see notes.md)
```

## 根因

`_find_ohos_native_sdk()` 只按「平铺」布局探测 libc++ 头文件路径：

```python
os.path.isdir(os.path.join(c, "include", "libcxx-ohos", "include", "c++", "v1"))
```

即期望 `<sdk>/include/libcxx-ohos/include/c++/v1`。但 CI worker 的 OHOS SDK 是
**llvm 嵌套**布局——SDK root 为 `<sdk>/ohos/native`，llvm 工具链与头文件在它的
`llvm/` 子目录下：

```
<worker-sdk>/ohos/native/llvm/include/libcxx-ohos/include/c++/v1
```

探测函数对 worker 候选路径（`glob("/data/service/hnp/ohos-sdk.org/*/ohos/native")`）
判定失败 → 返回 None → 配置期抛错，`conan create` 中断。本地开发机 SDK
（`/storage/Users/currentUser/ohos-sdk`）是平铺布局，探测命中 → 本地构建通过。

知识库中 ccrtp/bcc 等配方已使用 `.../ohos/native/llvm/include/libcxx-ohos/...`
（llvm 嵌套）路径，佐证 worker 布局，但缺少对「探测须兼容两种布局」这一模式的沉淀。

## 修复方案

探测时对每个候选 root 同时尝试平铺与 llvm 嵌套两种布局，命中任一即返回：

```python
for c in candidates:
    # 兼容两种 SDK 布局：扁平（<sdk>/include/libcxx-ohos/...，本地）与
    # CI worker 的 llvm 嵌套（<sdk>/llvm/include/libcxx-ohos/...）。
    for sdk in (c, os.path.join(c, "llvm")):
        if os.path.isdir(os.path.join(sdk, "include", "libcxx-ohos", "include", "c++", "v1")):
            return sdk
return None
```

`conanfile.py` 与 `test_package/conanfile.py` 需同步修改。

## 验证

1. 本地：`conan create archives/a/apt-pkg/2.7.14 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build=apt-pkg/*` 通过（平铺布局仍命中）。
2. CI：worker 上同命令在 llvm 嵌套布局下命中 `c/llvm`，构建全绿。
3. 回归：未修复版本在 worker 上报 `libcxx-ohos headers not found`；修复后不再出现。

## 适用与反例

适用：所有用 SDK 路径探测注入 OHOS libc++ 头文件/运行库的 conan 配方
（libffado、ccrtp、bcc 等同款实现），以及需在本地与 CI 两种 SDK 布局间迁移的 OHOS 构建。
反例：仅部署单一布局（如始终 llvm 嵌套）的环境不会暴露该问题，但探测函数
仍建议双布局兼容以降低环境迁移成本。
