# E560 — 压缩包根目录直接放文件（无顶层目录）：`get(strip_root=True)` 抛 ConanException

> **Status**: DRAFT（pending_editor_review）| **Severity**: 🟡 medium
> **Source**: tm-align/20190822 HarmonyOS PC AArch64 适配（feat/tm-align-20190822）

## 错误特征

```text
conan.errors.ConanException: Can't untar a tgz containing files in the root with strip_root enabled
# zip 对应：The zip file contains more than 1 folder in the root / The zip file contains a file in the root
```

复现（本地取证）：

```bash
tar tJf tm-align_20190822+dfsg.orig.tar.xz
# TMalign.f / TMalign.cpp / TMscore.f / TMscore.cpp   ← 无顶层目录
python3 -c "from conan.tools.files.files import untargz; untargz('tm-align_20190822+dfsg.orig.tar.xz', '.', strip_root=True)"
# ConanException: Can't untar a tgz containing files in the root with strip_root enabled
```

## 触发条件

- 构建系统: 任意；阶段: `source()`（`conan create` 最早一步）
- 源码包是 Debian `+dfsg` / 重打包 orig 压缩包，或科研小工具的平铺压缩包：根目录下直接是源文件，没有唯一顶层目录
- 配方沿用了模板里的 `get(..., strip_root=True)`

## 根因分析

`conan.tools.files.untargz` / `unzip` 的 `strip_root` 用成员路径的公共前缀判定顶层目录，要求恰有一个顶层目录；根目录直接是文件时没有公共目录，直接抛错。

附带现象：这类包没有任何构建系统文件，`init-build` / `conan-init` 回退判成 autotools，生成 `package_type = "library"` + `cpp_info.libs = ["<name>"]` 的骨架，不适用于只产出命令行工具的包。

## 解决方案

### 推荐方案

1. 先 `tar tf <源码包>` 看根结构；根目录平铺时 `source()` 写 `get(self, **self.conan_data["sources"][self.version])`，**不传 `strip_root`**（文件直接落在 `source_folder`）。
2. 无构建系统的包不要沿用自动骨架：`build()` 里用 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "clang++")` 取编译器直接编译；`package_type = "application"`，`package_info` 设 `libdirs = []`、`includedirs = []`、`bindirs = ["bin"]`。

### 禁止做法

- ❌ 自行用 `tar --strip-components` 重新打包后上传或换源：改变 sha256、偏离官方源（R39 / PF7）
- ❌ 为了套 `strip_root=True` 在 `source()` 里先手工解压再搬目录：绕开 `conandata.yml` 的 url / sha256 校验链

## 验证

```bash
python3 -c "from conan.tools.files.files import untargz; untargz('tm-align_20190822+dfsg.orig.tar.xz', '.', strip_root=True)"   # 期望抛 ConanException
conan create archives/t/tm-align/20190822 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64   # 去掉 strip_root 后通过
```

## 关联条目

- 查重：`engine` 对 strip_root / 根目录文件签名无命中；`knowledge/{graph,drafts,doc}` 检索 `files in the root` / `more than 1 folder in the root` 命中 0 条。
- 同族但不同：E430（`binfmt` 无 loader，本包本地验证同样用静态重链 + qemu，处置沿用）。
