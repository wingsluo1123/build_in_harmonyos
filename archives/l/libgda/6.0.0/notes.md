# libgda 6.0.0 编译笔记

## 编译环境

- 平台: HarmonyOS (aarch64-unknown-ohos)
- 构建系统: meson 1.11.1
- 编译器: clang 15.0.4

## 依赖版本

- glib-2.0: 2.88.0
- libxml-2.0: 2.13.5
- sqlite3: 3.49.1
- iso-codes: 4.16.0
- valac: 0.56.17
- intltool: 0.51.0

## 编译过程

1. **下载源码**: 从 GNOME FTP 镜像下载 libgda-6.0.0.tar.xz
2. **配置**: 使用 meson setup，禁用可选功能以减少依赖
3. **修复**: libxml-2.0.pc Cflags 头文件路径修正
4. **编译**: ninja -C build，460 个目标全部成功
5. **安装**: DESTDIR staging + 本地安装

## 关键修复

### libxml-2.0.pc Cflags 修复

原始 pkg-config 返回 `-I${includedir}`，但头文件实际在 `libxml2/` 子目录下。
修改为 `-I${includedir}/libxml2`，解决 `'libxml/tree.h' file not found` 错误。

## 编译配置

```bash
meson setup build --prefix=$HOME/usr/local \
  -Dui=false -Dexperimental=false -Dtools=false \
  -Ddoc=false -Dexamples=false -Djson=false \
  -Dlibsoup=false -Dlibsecret=false
```

## 质量门禁

- G1: PASS (库大小 15.7MB)
- G2: PASS (pkg-config 版本 6.0.0)
- G3: PASS (71 个头文件)
- G4: PASS (SQLite provider 存在)

## 编译状态

**built** - 编译成功，可正常使用

## Conan 适配 (2026-08-10)

### Conan 配方

- conanfile.py: 使用 Meson + MesonToolchain
- conandata.yml: 源码 URL + sha256 + 补丁
- test_package/: CMake L1 测试

### 依赖 (Conan)

- glib2/2.88.0 (conan 制品仓)
- libxml2/2.15.3.1 (conan 制品仓)
- sqlite3/3.49.1 (conan 制品仓)

### 依赖 (系统/pkg-config)

- iso-codes/4.16.0 (cmd-pkgs 预编译)
- json-glib/1.6.6 (cmd-pkgs 预编译)
- libsoup/2.74.3 (cmd-pkgs 预编译)
- valac/0.56.18 (cmd-pkgs 预编译)
- intltool/0.51.0 (cmd-pkgs 预编译)

### 构建选项 (无裁剪)

- json=true (json-glib 可用)
- libsoup=true (libsoup 可用)
- sqlcipher=true (sqlcipher 可用)
- ui=false (GTK 未适配)
- tools=false (实验性)
- experimental=false
- doc=false
- examples=false

### OHOS 平台适配

1. **lld 链接器问题**: lld 依赖 libxml2.so.16，在 OHOS 上加载失败。使用 `-fuse-ld=/data/service/hnp/bin/ld` 强制 GNU ld
2. **Vala 编译器**: OHOS execvp 无法通过 PATH 查找二进制。通过 meson native file 指定完整路径
3. **glib-mkenums**: 系统版本使用 Perl 脚本（shebang 不兼容），使用 Python3 版本（cmd-pkgs glib 2.88.0）
4. **glib 子库 .pc 文件**: glib2 conan 包只生成 glib-2.0.pc，手动创建 gio-2.0.pc, gobject-2.0.pc 等
5. **交叉编译**: 使用 build profile (os=Linux) + host profile (os=OHOS) 触发 meson cross-file 生成，跳过 sanity check
6. **compiler.run() 补丁**: 交叉编译模式下 meson 无法运行测试程序，添加补丁跳过

### 已知限制

- OHOS 安全策略阻止执行新编译的 ELF 二进制文件 (mkkeywordhash, lemon 等)
- 这是 HarmonyOS 平台限制，需要 CI worker 环境或二进制签名机制

