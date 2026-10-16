# 自研安装器只装运行库 —— Conan 打包须补开发软链与静态库

> **草稿状态**：本文件为 `knowledge/drafts/` 下的 draft，尚未经主编审核合入正式库。
> 关联条目：`DRAFT-netpbm-10.73.42-legacy-installer-package-layout.kv`
> 来源：netpbm 10.73.42 适配实测（2026-10-15，HarmonyOS PC aarch64）

## 1. 触发场景

上游用**自研安装器**（`install.sh`、`make package pkgdir=DIR`、私有 `make install prefix=` 等），
而不是 autotools / CMake / Meson 的 `make install DESTDIR=`。典型特征：

- 顶层只有一个手写 `Makefile` + `install.sh`（netpbm 是 `GNUmakefile` + `install.sh` +
  交互式 `configure.pl`）；
- 安装入口接受 `pkgdir`（而非 `DESTDIR`），并用 `mkdir`（**非** `mkdir -p`）创建目标目录；
- 安装规则只考虑**运行期**需要的东西。

在这类包上跑 `conan create`，会在两个不同阶段各挂一次。

## 2. 症状与报错特征

| 阶段 | 现象 | 报错特征 |
|---|---|---|
| `package()` | 安装器拒绝写入 | `mkdir: cannot create directory ...: File exists`、`Directory <...> already exists` |
| `test_package` / 消费方 | 链接失败 | `Library 'netpbm' not found in package`（CMakeDeps）、`cannot find -lnetpbm` |

## 3. 根因

### 3.1 安装器假定目标目录不存在

Conan 在执行 `package()` **之前**已经创建好 `package_folder`；而 `netpbm-init_package`
用 `mkdir`（无 `-p`）创建 `pkgdir`，目录已存在即失败退出。

### 3.2 开发用链接产物留在构建树，没进安装目录

上游 `install.sh` 只装运行期需要的东西：

```
<package>/lib/libnetpbm.so.11.73     ← 真文件
<package>/lib/libnetpbm.so.11        ← soname 软链
```

而开发用的：

```
<build>/lib/libnetpbm.so             ← `-l` / CMakeDeps 的查找入口
<build>/lib/libnetpbm.a              ← 静态库
<build>/link/libnetpbm.a             ← 上游自建的便捷目录（又一整份副本）
```

**都留在构建树里**。ConanDeps 只在包 `libdirs` 内按 `lib<name>.so` / `lib<name>.a`
精确匹配文件名，带版本号的 `.so.11.73` 不匹配 → `Library 'netpbm' not found in package`。

**判读要点**：这不是"库没编译出来"，而是"装出来的文件名不符合消费方约定"。误判成上游
源码缺陷会走向错误方向（去查源码/链接命令），实际只需补齐安装产物。

## 4. 处理策略

### ① 交还目录创建权

```python
def package(self):
    # Conan 预建了 package_folder，而上游 init_package 用 mkdir（无 -p）→ 先删
    if os.path.isdir(self.package_folder):
        rmdir(self, self.package_folder)
```

### ② 安装完成后补齐开发链接产物（幂等）

```python
def _complete_link_artifacts(self):
    libdir = os.path.join(self.package_folder, "lib")
    if not os.path.isdir(libdir):
        return
    # 开发软链：libX.so -> 点数最少的 libX.so.<major>（相对软链，便于整包搬运）
    sonames = sorted(n for n in os.listdir(libdir) if n.startswith("libnetpbm.so."))
    dev = os.path.join(libdir, "libnetpbm.so")
    if sonames and not os.path.lexists(dev):
        os.symlink(sonames[0], dev)
    # 静态库：构建树 → 包内
    src = os.path.join(self.source_folder, "lib", "libnetpbm.a")
    if os.path.isfile(src) and not os.path.exists(os.path.join(libdir, "libnetpbm.a")):
        copy(self, "libnetpbm.a", src=os.path.dirname(src), dst=libdir, keep_path=False)
    # 清理上游便捷目录，避免静态库在包内出现两份
    rmdir(self, os.path.join(self.package_folder, "link"))
```

### ③ 判据（如何确认真的修好了）

```bash
ls -l <package>/lib                          # 应同时看到 .so.11.73 / .so.11 / .so / .a
readlink <package>/lib/libnetpbm.so          # → libnetpbm.so.11
conan create archives/n/netpbm/10.73.42 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
```

netpbm 实测：补齐后 `conan create` exit=0，`test_package` 中 CMake `find_package(netpbm)`
+ ctest 100% passed。

## 5. 适用库范围

- 自研 Makefile + `install.sh` 安装体系（无 autotools/CMake/Meson）；
- 产物含共享库，且安装规则只装版本化运行库；
- 已知实测：netpbm 10.73.42。

不适用：走 CMake `install(TARGETS ...)` 的项目（CMake 会自动生成 dev 软链与 `.a`），
以及 `make install DESTDIR=` 遵循 GNU 惯例的项目。

## 6. 限制与反例

- **不要整目录拷贝兜底**：`copytree`/`cp -r` 会把 `.o`、测试二进制一起塞进包，包体膨胀且
  引入不可复现内容（L5 产物基线会漂移）。只按需拷贝目标文件。
- **软链方向**：必须用**相对**软链（`os.symlink("libX.so.11", "libX.so")`），绝对软链在包被
  搬运/缓存后会指向错误位置。
- **HMDFS 软链限制**：部分挂载点不允许创建软链（参见
  `DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink`）；此时兜底为在
  `cpp_info.libs` 里声明带版本号的文件名，但会破坏 `-l<name>` 惯例，仅作最后手段。

## 7. 复现脚本

```bash
#!/bin/sh
# 复现"安装器只装运行库"造成的消费方链接失败（netpbm 10.73.42 实例）
# 前置：已 clone build_in_harmonyos，且制品仓含 zlib/libpng/libjpeg-turbo/libtiff
set -e
PKG=archives/n/netpbm/10.73.42

# 1) 关掉配方中的补齐逻辑（注释掉 _complete_link_artifacts 调用）后构建：
#    期望在 test_package 阶段报 "Library 'netpbm' not found in package"
conan create "$PKG" -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing

# 2) 打开补齐逻辑，重复上述命令：期望 exit=0，ctest 全过
# 3) 对照包内 lib 布局
find ~/.conan2/p -maxdepth 4 -name 'libnetpbm.*' -path '*netpbm*'
```

## 8. 关联知识

- `DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink` —— 反向场景（CMake 版本化软链
  在 HMDFS 上创建失败，要求去掉版本化）；
- `DRAFT-libharu-2.3.0-missing-dt-soname` —— 文件在但缺 `DT_SONAME`；
- `DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing` —— raw Makefile CLI 的 POSIX 兼容与 ELF 签名。
