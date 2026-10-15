# E549: CMake 安装期剥离 RPATH 的 ELF 在 OHOS 上 dlopen 报 EACCES

## 问题描述

用 CMake 构建并安装的 shared library，在 OHOS 上加载失败：

```
Error loading shared library /path/to/libfoo.so.30: Permission denied
```

诡异之处在于**同一份代码**：

- 构建目录里的 `libfoo.so.30` → `dlopen` 成功；
- `cmake --install` 装出来的 `libfoo.so.30` → `dlopen` 报 `Permission denied (EACCES)`。

`chmod 777` 无效；把安装副本复制到别的目录仍失败 —— 排除权限/挂载/路径因素，是**内容差异**。

## 错误特征

```
Error loading shared library libobs.so.30: Permission denied
Error relocating ./test_bin: symbol not found: <被测符号>
```

`readelf` 对比安装副本与构建副本：

- `readelf -l`（程序头）**逐字节一致**；
- `readelf -n`（`.note.ohos.ident`）**逐字节一致**；
- 唯一差别：安装副本的 `.dynamic` 里**少一条 RUNPATH**。

## 根本原因

CMake 默认行为：

1. 构建期给每个 shared object 写入 build-tree RPATH；
2. `cmake --install` 阶段**原地改写 ELF**（`cmRemoveRPath`），把载入路径重写为
   `INSTALL_RPATH`（通常为空）从而剥离它。

OHOS 的加载器（musl 派生）对「被安装期改写过的 ELF」返回 `EACCES` — 文件仍是合法 ELF
（`readelf` 一切正常），但加载器拒绝映射。这是平台加载器行为差异，不是 CMake 或文件的元数据问题。

## 解决方案

### 方法：让 CMake 完全不要碰 RPATH

```python
# conanfile.py — generate()
tc = CMakeToolchain(self)
tc.variables["CMAKE_SKIP_RPATH"] = "ON"   # 关键
tc.generate()
```

`CMAKE_SKIP_RPATH=ON` 同时取消构建期写入与安装期改写，ELF 保持原样。运行期依赖交给
conan run 环境（`LD_LIBRARY_PATH`）或消费方自身的 RPATH —— 这也符合 conan 包不应内嵌
绝对 RPATH 的惯例。

等价的替代写法：`CMAKE_BUILD_WITH_INSTALL_RPATH=ON` + `CMAKE_INSTALL_RPATH` 为空。

**不要**使用 `CMAKE_INSTALL_RPATH_USE_LINK_PATH` 之类把 conan 缓存绝对路径写进包里的方案。

### 复现 / 验证

```c
/* dlt.c — 用 dlopen 观察真实错误（OHOS 的 /tmp 只读，用 $TMPDIR 或 $HOME/tmp） */
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char **argv) {
    void *h = dlopen(argv[1], RTLD_NOW);
    printf("handle=%p err=%s\n", h, dlerror());
    return h ? 0 : 1;
}
```

```bash
clang dlt.c -o dlt
./dlt <build-tree>/lib/libfoo.so.1          # handle 非 0
./dlt <DESTDIR>/usr/local/lib/libfoo.so.1   # Permission denied
readelf -d <installed>.so | grep -c RUNPATH # 0（构建副本为 1）
```

## 影响范围

所有用 CMake 构建、安装 shared library / MODULE 且默认生成 build RPATH 的三方库，
尤其是「主库 + 多个可加载模块」的大型项目（install 阶段会批量改写所有目标）。

## 关联

- 排查时容易先怀疑：文件权限、HMDFS/SELinux、noexec 挂载、代码签名 —— 均可通过
  「构建副本可加载、安装副本不可加载」这一对照实验快速排除。
- 相关：OHOS 只读 `/tmp`（E002）。

## 实例

obs 32.1.2（`libobs.so.30`）：安装副本 `dlopen` 报
`Error loading shared library .../libobs.so.30: Permission denied`，
加 `CMAKE_SKIP_RPATH=ON` 后构建/安装副本均可正常加载，`conan create` 与
`test_package` 全部通过。
