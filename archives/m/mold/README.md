# mold

mold is a high-performance drop-in replacement for the GNU linker ld, designed to be significantly faster than other linkers.

## 基本信息

- **名称**: mold
- **主页**: https://github.com/rui314/mold
- **许可证**: MIT
- **分类**: tool (command-line tool)

## 鸿蒙适配要点

### 关键适配

1. **C++20 std::ranges 兼容** (0001-lib-common.h.patch)
   - OHOS libc++ 缺少完整的 C++20 `std::ranges` 支持
   - 用自定义 `namespace ranges` 实现替代 `std::ranges` 的所有算法调用

2. **C++20 spaceship operator 兼容** (0002-src-gdb-index.cc.patch)
   - OHOS libc++ 缺少 `operator<=>` 支持
   - 用 `#ifdef __OHOS__` 守卫，手动实现 `operator<` 和 `operator==`

3. **禁用 mimalloc** (`MOLD_USE_MIMALLOC=OFF`)
   - mimalloc 在 OHOS 上有兼容性问题
   - 使用系统 malloc 替代

4. **内置依赖**
   - mold 内置了 zlib, blake3, zstd, TBB，不需要额外 conan 依赖

5. **CMAKE_INSTALL_LIBEXECDIR 修复**
   - CMake 不识别 OHOS 平台，GNUInstallDirs 将 LIBEXECDIR 默认为 "bin"
   - 导致 bin/mold/ld 符号链接与 bin/mold 二进制文件冲突
   - 强制设置为 "libexec" 解决路径冲突

### CMake 配置示例

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DMOLD_USE_MIMALLOC=OFF \
      -DCMAKE_INSTALL_LIBEXECDIR=libexec \
      ..
make -j2
make install
```

### 验证

```bash
mold --version
# Expected: mold 2.39.1 (compatible with GNU ld)
```

## 编译历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 2.39.1 | built | 2026-08-07 | Conan 配方适配 |

## 依赖关系

mold 内置了所有第三方依赖（zlib, blake3, zstd, TBB），无外部 conan 依赖。
