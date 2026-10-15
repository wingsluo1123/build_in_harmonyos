# DRAFT-libfprint-1.94.10-contents-api-truncated-conanfile-empty-package

contents API 推送截断 conanfile.py → 缺 build/package 方法 → Conan 空包 → test_package include 路径不存在(E650 同族,与 DRAFT-libkysdk 字节损坏同类)

## 现象

PR #14631(libfprint 1.94.10)构建 #80061 在 `conan-build-test` 步骤失败:

```
libfprint/1.94.10: package(): WARN: No files in this package!
CMake Error: Imported target "libfprint::libfprint" includes non-existent path
  ".../p/include"
[error] conan create failed
```

prepare/git-clone/checkout-pr/conan-setup 全 ✅,仅 conan-build-test ❌。
本地同配方同命令 CI 全绿(RC=0),与 PR CI 矛盾。

## 根因

远端 `conanfile.py` 经 contents API 推送时被**截断**(4299B / 90 行 vs 本地 20707B / 431 行,
停在 `requirements()` 注释处),缺全部 `build()/package()/generate()/package_info()` 方法。
Conan 对无 `package()` 的配方默认空操作 → 空包 `No files in this package!` →
CMakeDeps 生成 `INTERFACE_INCLUDE_DIRECTORIES=<pkg>/include` 指向不存在的目录 →
test_package `find_package` 配置时报 "includes non-existent path" → conan create 失败。

与 DRAFT-libkysdk(字节损坏→PR diff 判二进制→checkout-pr 死)同源(推送链路损坏),
但本类表现是**文件截断仍为文本、checkout-pr 能过、故障在 conan create 阶段**;
与 picojson(相对 dst 空包)错误面相同("No files in this package!")但根因不同(推送损坏 vs 配方 bug)。

## 最小判据(一行)

```
# 对比远端 raw 与本地(应无输出=已一致)
curl -sL "https://atomgit.com/{owner}/{repo}/raw/{branch}/archives/l/libfprint/1.94.10/conanfile.py" | cmp - <本地conanfile.py
# 远端 conanfile 是否缺核心方法
curl -sL "https://atomgit.com/{owner}/{repo}/raw/{branch}/.../conanfile.py" | grep -cE "def (build|package|package_info)"
```

## 推荐方案:push-clean-files-verify-bytes

1. 本地 CI 先跑与 PR 完全相同的 `ci/conan/build_and_test.sh`(注入 `CI_BRANCH=<分支名>` 与 `CONAN_PROFILE`),确认本地配方正确;
2. 用本地干净文件经 contents API `PUT` 覆盖远端截断版——必须带 `branch=<源分支>` + `sha`(旧 blob)+ `content`(base64,**零空格**);
3. 推送后**字节级对比**远端 raw 与本地(`cmp` 应无输出),确认转码/截断不再发生;
4. 再触发 `/rebuild`。

## 禁止事项

- ❌ 对 `No files in this package!` 反复 `/rebuild`(远端文件损坏,确定性失败);
- ❌ 在本地已通过的配方上瞎改(根因在推送链路,不在配方);
- ❌ contents API PUT 不带 `branch` 参数(404 Blob Not Found,默认落到 main)。

## 关系

- similar_to: DRAFT-libkysdk-3.0.1.0-contents-api-byte-corruption-binary-patch-diff(同为推送字节损坏,表现不同)、DRAFT-picojson-1.3.0-conan-copy-absolute-dst(同为空包错误面)
- 适用原则: W2(PR 原子性)、W3(本地编译验证)

---
*由 libfprint 1.94.10 PR #14631(构建 #80061)修复过程沉淀,2026-10-11*
