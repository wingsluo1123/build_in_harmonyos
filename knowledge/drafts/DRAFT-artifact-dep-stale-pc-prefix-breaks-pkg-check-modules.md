# 制品仓发布的依赖包 .pc 内嵌打包机会话绝对路径 → 消费方 CMake pkg_check_modules 校验失败，应在消费方 generate() 复制 .pc 改写三行并前置 PKG_CONFIG_PATH

- **草稿 ID**: DRAFT-artifact-dep-stale-pc-prefix-breaks-pkg-check-modules
- **严重度**: 2
- **类别**: conan, packaging, pkgconfig, cmake, linking, relocatable
- **来源案例**: hyprlang 0.5.3 适配（HarmonyOS PC aarch64，消费制品仓 hyprutils/0.3.0）；同族案例 cfitsio.pc、cairo/poppler .pc
- **同族关系**: 与 DRAFT-ccfits-2.7-stale-pc-prefix-regen、DRAFT-pdf2svg-0.2.4-dep-bundled-pc-build-prefix-pollution 为同一问题族三个实例（失败面各异）；合并/收编与最终编号由知识库主编裁决，本草稿不自行合并。

## 错误特征

消费方 CMake 在 **generate 阶段**直接 fatal（不推迟到编译期、不静默）：

```
CMake Error in CMakeLists.txt:
  Imported target "PkgConfig::deps" includes non-existent path
    "/storage/Users/currentUser/.cache/conan2/p/b/hypru*/p/include"
```

**引文来源说明**：以上 fatal 为 Curator 自包含探针复现（设备
`tmp/oh-device-porting-v2/curator-probe-pc/`，CMakeLists + dummy.c +
`PKG_CONFIG_PATH=<制品包>/lib/pkgconfig cmake ..`，任何人不依赖本 run 可重跑）。
本 run 无 pre-fix 实败日志——.pc 修复是配方对既有模板的预防性加固，如实记录；
探针同时验证了修复端到端成立（sed 改写三行后 `Configuring done / Generating done`）。

**辨别性指纹**：路径前缀是打包机的 `.cache/conan2/p/b/<hash>/p`（conan 源码打包
会话临时目录），而消费机缓存是 `.conan2/p/<hash>/p` —— 两个布局错位，路径必然
失效。看到 `prefix=/` 则是 E355 空根变体。

## 根因分析

制品仓发布的依赖包（案例 hyprutils/0.3.0）内 `lib/pkgconfig/*.pc` 三行全是打包机
conan 源码打包会话目录（消费机不存在）：

```
prefix=/storage/Users/currentUser/.cache/conan2/p/b/hypru393d424d3ded0/p
includedir=/storage/Users/currentUser/.cache/conan2/p/b/hypru393d424d3ded0/p/include
libdir=/storage/Users/currentUser/.cache/conan2/p/b/hypru393d424d3ded0/p/lib
```

与 E355 记录的 pixman `prefix=/`（空根）同族，但变体不同：**绝对路径存在但指向
打包机会话的临时目录**。CMake `pkg_check_modules(... IMPORTED_TARGET)` 会在
generate 阶段校验 Imported target 的 include 路径存在性，坏路径直接 fatal；
即使不被校验拦下，`-L` 失效也会让链接期重新踩坑。

注意与 E537（DT_NEEDED 绝对路径泄漏）区分：E537 是 ELF 层（依赖无 SONAME 时
ld 记录 IMPORTED_LOCATION 绝对路径），本条是 pkg-config 元数据层；同一个发布包
两者可以同时存在，消费方要分别处理。

## 推荐方案

**方法**: 消费方 recipe 的 `generate()` 里复制依赖 .pc 到生成目录并改写三行，
`PKG_CONFIG_PATH` 前置命中修正版（案例：hyprutils 配方对 pixman-1.pc 的同款机制，
key 从 prefix 扩展为 prefix/includedir/libdir 三行）：

```python
fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
content = re.sub(r"(?m)^includedir=.*$", f"includedir={base}/include", content)
content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)
```

`base` 取 `dep.package_folder`（消费时 conan 缓存里的真实路径）。不要试图改
制品仓已发布的包——那是越界且不可复现的；也不要用 patchelf 事后修 ELF（HMDFS
上 mmap PROT_EXEC 会被拒，见 E537）。

## Fallback（退路，诚实权衡）

若 .pc 只有部分 key 失效，可在 generate() 里用 `-isystem` 注入 dep include 目录 +
toolchain 注入链接目录绕开 .pc 的 Cflags/Libs。**权衡**：丢掉 .pc 的 Requires
传播与版本约束检查，掩盖元数据失效而非修复，仅作临时手段。

## Forbid（反模式）

- 直接改写制品仓缓存里的已发布包 —— 越界且不可复现，污染其他消费方（审查 P0 打回）。
- package()/post-build 用 patchelf 改 .pc 或 ELF —— HMDFS 上 mmap PROT_EXEC 拒绝（E537）。
- 只改 prefix 不改 includedir/libdir —— pkg-config 优先用绝对 includedir/libdir，等于没修，configure 仍报 non-existent path。

## 排查提示

1. `cat <dep_pkg>/lib/pkgconfig/*.pc | grep prefix` —— 看到
   `.cache/conan2/p/b/` 即本条（打包机会话残留）；看到 `prefix=/` 是 E355 变体。
2. `ls $(dirname <pc>)/../include` 对照真实包路径确认失效。
3. 修完后用 `PKG_CONFIG_PATH=<fixed_dir> pkg-config --cflags --libs <name>`
   或直接跑 CMake configure 验证。

## 自包含验证序列（不依赖本 run 日志）

OHOS 设备 /tmp 只读，`PROBE` 用可写目录（如 run tmp）：

```
PROBE=<scratch_dir> && mkdir -p $PROBE && cd $PROBE
# ① 指纹
grep prefix <dep_pkg>/lib/pkgconfig/<dep>.pc        # .cache/conan2/p/b/<hash>/p → 本条
# ② 复现 CMake generate 阶段 fatal
printf 'project(pcprobe)\ncmake_minimum_required(VERSION 3.20)\nfind_package(PkgConfig REQUIRED)\npkg_check_modules(DEPS REQUIRED IMPORTED_TARGET <dep>)\nadd_library(pcprobe SHARED dummy.c)\ntarget_link_libraries(pcprobe PRIVATE PkgConfig::DEPS)\n' > CMakeLists.txt
#   （后两行必须要有：CMake 只校验被 target 消费的 Imported target，缺消费则不触发 fatal）
printf 'int main(void){return 0;}\n' > dummy.c
PKG_CONFIG_PATH=<dep_pkg>/lib/pkgconfig cmake .
#   → Imported target "PkgConfig::DEPS" includes non-existent path，Generate step failed
# ③ 修复验证：sed 改写 .pc 三行（prefix/includedir/libdir → 真实包路径）后，
#   换干净目录（或清 CMakeCache.txt）重跑——pkg_check_modules 的 DEPS_* 变量
#   会缓存进 CMakeCache，fatal 后同目录直跑会误报修复无效
PKG_CONFIG_PATH=<fixed_pc_dir> cmake .
#   → Configuring done / Generating done
```

## 原则挂钩（P 编号）

- **P014**（环境变量与构建系统语义冲突陷阱）：修复走构建系统原生机制 `PKG_CONFIG_PATH`，不靠 C_INCLUDE_PATH/LIBRARY_PATH 类散变量。
- **P016**（HMDFS 文件系统限制必须用替代方案）：patchelf/改制品包路线在 HMDFS 上注定失败，必须用消费方改写替代。
- **P013**（平台限制必须降级而非绕过）：fallback 仅作降级退路并如实声明权衡，不冒充修复。

（原自由命名 real-evidence-over-assumption / minimal-patch / relocatable-artifacts / boundary-discipline 已按 Curator 审计对齐为上述 P 编号；最终以主编确认为准。）

## 关键词

pkg_check_modules, hyprutils.pc, prefix, includedir, libdir, 打包机,
.cache/conan2, non-existent path, Imported target, PKG_CONFIG_PATH,
fixed_pkgconfig, relocatable, E355, E537, E383, hyprlang
