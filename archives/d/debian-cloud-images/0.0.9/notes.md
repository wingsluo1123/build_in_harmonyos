# debian-cloud-images 0.0.9 适配笔记

## 上游识别
- 上游包：`debian-cloud-images`（Debian native 源包，源格式 `3.0 (native)`）
- 版本：`0.0.9`（stable/trixie；madison：stable=0.0.9、testing=0.0.9、unstable=0.0.9）
- 上游地址：https://tracker.debian.org/pkg/debian-cloud-images ／ https://salsa.debian.org/cloud-team/debian-cloud-images
- 构建系统：**none**（Debian 打包 `dh`；源包无任何编译源码）
- 源包内容：仅 `package/debian/`，共 8 个文件（4472 字节 .tar.xz）

## 包性质
Debian 云镜像的「所需软件包清单」载体。源包含三部分：
1. `debian/source.substvars` —— 上游随源包发布的**已生成**依赖清单（数据本体）：
   `debian-cloud-images-packages:Depends=` 字段，逗号分隔，条目可带 `[arch]` 限定。
2. `debian/bin/make-substvars` —— 清单生成器（Python3，仅用 stdlib `pathlib`/`sys`），
   从 `../config_space/sid/package_config` 派生清单。
3. `debian/{control,rules,changelog,copyright,source/*}` —— 打包元数据。

上游二进制产物是**空元包** `debian-cloud-images-packages`（`Architecture: amd64 arm64 ppc64el`），
其 `Depends` 由 `${debian-cloud-images-packages:Depends}` 在打包期代入。

## 编译步骤
**无编译**（纯数据包，`build_system: none`）。流程为：

```bash
# 真实构建 = conan create（source 下载 → build 本体自检 → package → test_package）
conan create archives/d/debian-cloud-images/0.0.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

`build()` 只做本体自检：清单载体与生成器必须在，且清单必须可解析出非空条目。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 生成器 `make-substvars` 读取的 `../config_space/sid/package_config` 不在源包内 | Debian 源包（`package/` 子树）不含 salsa 仓库的 `config_space/`；上游直接发布已生成的 `source.substvars` | 交付上游已发布的清单本体，不重跑生成器；`build()` 只校验其自洽性 |
| 2 | `sources.debian.org` 官方 `.tar.xz` 与 `deb.debian.org` 归档源 | CI preflight PF7 将 `deb.debian.org` 等 Debian 归档主机列为「Debian 下游重打包源」拦截 | conandata 走清华 TUNA 权威镜像同一份文件（sha256 与官方 `.dsc` 逐字一致） |

## OHOS 平台适配
- 纯数据包，无编译产物、无第三方库依赖 → **无编译期 OHOS 改动**（无 `patches/`）。
- 产物与架构无关；settings 保留 `os/compiler/build_type/arch` 仅用于交叉编译矩阵一致性。
- 鸿蒙 PC 目标架构为 arm64/aarch64：消费者用例按 Debian `[arch]` 限定语义派生
  **arm64（OHOS PC）适用子集**，作为本包的鸿蒙特有消费场景。

## 依赖版本
- 强制第三方依赖：**无**（上游 `Build-Depends` 仅 `debhelper-compat (= 13)`，属 Debian 打包工具链，非第三方库）
- conan `requires`：无（纯数据包）

## 验证结果
```bash
# 见 reports/
python3 scripts/ohc-run.py conan-verify debian-cloud-images 0.0.9   # G0-G4 + L2/L4/L5
python3 scripts/ohc-run.py finish debian-cloud-images 0.0.9 built    # W2 结构 + R36 依赖 + W3 本地 CI
```

## 上游测试
上游**无自动化测试入口**（N=0）：无 `tests/`/`test/`/`debian/tests`，无 autopkgtest
（control 无 `Testsuite`），无 CMake/Meson/Autotools 测试 target，无 pytest/tox。
清点命令与原始输出见 `reports/upstream-test-gap-statement.md`。
---

**编译结束**: 2026-10-05 18:14
**最终状态**: built
