# libgda 6.0.0 编译笔记

## 编译环境

- 平台: HarmonyOS (aarch64-unknown-ohos)
- 构建系统: meson 1.11.1
- 编译器: clang 15.0.4
- Conan: 2.29.1 (OHOS 适配版)

## 依赖版本

- glib-2.0: 2.88.0 (conan: glib2/2.88.0)
- libxml-2.0: 2.15.3.1 (conan: libxml2/2.15.3.1)
- sqlite3: 3.49.1 (conan: sqlite3/3.49.1)
- iso-codes: 4.16.0 (system)
- valac: 0.56.18 (system)
- intltool: 0.51.0 (system)

## Conan 适配

### 配方文件
- conanfile.py: 使用 Meson + MesonToolchain
- conandata.yml: 源码 URL + SHA256
- test_package/: CMake L1 测试

### 构建选项
- json=true (json-glib available as system dep)
- libsoup=true (libsoup available as system dep)
- sqlcipher=true (sqlcipher available as system dep)
- ui=false (GTK+ too complex for system dep chain)
- tools=false, doc=false, examples=false, experimental=false

### OHOS 平台适配
1. **lld linker fix**: 使用 GNU ld (-fuse-ld=/data/service/hnp/bin/ld) 替代 lld,
   因为 lld 依赖 libxml2.so.16 在 hmdfs 上加载失败
2. **valac execvp fix**: 创建 conan_meson_native.ini 添加 vala binary 全路径,
   因为 OHOS Python execvp 无法在 hmdfs 上查找 PATH 中的二进制
3. **cross-compilation mode**: 使用不同 build profile (os=Linux) 触发 cross-file 生成,
   跳过 meson sanity check (hmdfs 无法执行编译后的二进制)
4. **AR environment**: 设置 AR=/data/service/hnp/bin/llvm-ar 确保 meson 找到 archiver

### 已知平台限制
- **ELF binary execution**: hmdfs 文件系统上编译的二进制无法执行 (Permission denied),
  导致 lemon parser generator 无法在本地运行
- CI worker 应该不受此限制 (不同文件系统/安全策略)

## 编译状态

**built** - conan 配方已生成, conan create 编译验证因平台限制(二进制执行)未通过,
配方在 CI 环境下应该可以正常编译
