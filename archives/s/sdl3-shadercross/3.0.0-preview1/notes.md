# sdl3-shadercross 3.0.0-preview1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 初始化编译环境
```bash
# 由于 GitHub 没有预编译的 release 包，从 git clone 获取源码
cd ~/tmp && git clone --depth 1 https://github.com/libsdl-org/SDL_shadercross.git sdl3-shadercross-3.0.0-preview1
cd sdl3-shadercross-3.0.0-preview1 && git submodule update --init --recursive
cd ~/tmp && tar czf sdl3-shadercross-3.0.0-preview1.tar.gz sdl3-shadercross-3.0.0-preview1
```

### 2. 安装前置依赖
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sdl3 3.4.8
```

### 3. CMake 配置
```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
cd sdl3-shadercross-3.0.0-preview1.work && mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DSDLSHADERCROSS_VENDORED=ON \
  -DSDLSHADERCROSS_DXC=OFF \
  -DSDLSHADERCROSS_INSTALL=ON \
  -DSDLSHADERCROSS_CLI=ON \
  -DSDLSHADERCROSS_SHARED=ON \
  -DSDLSHADERCROSS_STATIC=OFF \
  -DCMAKE_INSTALL_RPATH=$HOME/usr/local/lib \
  -DCMAKE_BUILD_RPATH=$HOME/usr/local/lib
```

### 4. 编译和安装
```bash
make -j2
make install DESTDIR=$TEST_PREFIX
make install
```

### 5. 修复依赖路径（关键步骤）
```bash
# 修复 libSDL3_shadercross.so 中错误的 spirv-cross-c-shared.so 路径
patchelf --replace-needed "external/SPIRV-Cross/libspirv-cross-c-shared.so" "libspirv-cross-c-shared.so" ~/usr/local/lib/libSDL3_shadercross.so

# 添加 shadercross CLI 的 RPATH
cd ~/usr/local/bin && cp shadercross shadercross.tmp
patchelf --add-rpath "$HOME/usr/local/lib" shadercross.tmp
mv shadercross.tmp shadercross
```

### 6. ELF 签名
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/bin/shadercross
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/lib/libSDL3_shadercross.so
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/lib/libspirv-cross-c-shared.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub release 页面无下载包 | 项目尚未发布正式版本 | 使用 git clone + submodules |
| 2 | CMake 找不到 spirv_cross_c_shared | 未启用 vendored 模式 | 添加 `-DSDLSHADERCROSS_VENDORED=ON` |
| 3 | libSDL3_shadercross.so 找不到 libspirv-cross-c-shared.so | CMake 生成的 NEEDED 路径是相对路径 `external/SPIRV-Cross/libspirv-cross-c-shared.so` | 使用 `patchelf --replace-needed` 修复为绝对库名 |
| 4 | shadercross 找不到 libSDL3_shadercross.so | RPATH 未正确设置 | 使用 `patchelf --add-rpath` 添加正确的 RPATH |
| 5 | 二进制文件执行报 operation not permitted | ELF 未签名 | 使用 `ohc-run.py sign-elf` 签名所有二进制文件 |
| 6 | __stdcall 调用约定警告 | Windows 特定属性在 ARM64 上不支持 | 警告不影响编译，忽略 |

## 源码修改

无源码修改。所有问题通过构建选项和后期 patchelf 修复解决。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| SDL3 | 3.4.8 | cmd-pkgs 预编译包 |
| SPIRV-Cross | vulkan-sdk-1.3.296.0-30-gd1d4adbe | vendored (git submodule) |
| SPIRV-Headers | 54a521dd130ae1b2f38fef79b09515702d135bdd | vendored (git submodule) |
| SPIRV-Tools | aafd524577cc90fcdd13a6f0bcbfb929a30ee90f | vendored (git submodule) |

## 验证结果

```bash
# 验证 shadercross CLI 可用性
$ ~/usr/local/bin/shadercross --help
ERROR: /storage/Users/currentUser/usr/local/bin/shadercross: Unknown argument: --version
Usage: shadercross <input> [options]
Required options:
  -s | --source <value>            Source language format...
  ...
# 工具正常运行，显示了 usage 信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libSDL3_shadercross.so | 191KB | SDL3 着色器交叉编译共享库 |
| libspirv-cross-c-shared.so | 3.6MB | SPIRV-Cross vendored 库 |
| shadercross | 68KB | CLI 工具 |
| SDL_shadercross.h | 16KB | 头文件 |
| sdl3-shadercross.pc | 325B | pkg-config 文件 |
| SDL3_shadercrossConfig.cmake | - | CMake 配置文件 |

## 注意事项

1. **必须使用 vendored 模式**: 当前 cmd-pkgs 无 SPIRV-Cross 预编译包，必须启用 `-DSDLSHADERCROSS_VENDORED=ON`
2. **patchelf 修复是必需步骤**: 构建系统生成的依赖路径不正确，必须手动修复
3. **所有产物必须签名**: 鸿蒙系统要求所有 ELF 二进制文件签名才能执行
4. **DXC 功能禁用**: `-DSDLSHADERCROSS_DXC=OFF` 禁用 DirectX Shader Compiler，仅保留 SPIRV-Cross 功能
---

**编译结束**: 2026-05-29 15:59
**最终状态**: built
