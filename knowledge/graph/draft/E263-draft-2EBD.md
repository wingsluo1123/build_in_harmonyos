# E263 — 上游 CMake 写死 FFTW_VERSION 3.3.9 泄漏到 fftw3.pc 的 Version 字段

## 错误特征
- `pkg-config --modversion fftw3` 输出 `3.3.9`，而实际打包发布版本是 `3.3.10`。
- 安装产物 `lib/pkgconfig/fftw3.pc` 中 `Version: 3.3.9`。
- 源码 `CMakeLists.txt` 中存在 `set (FFTW_VERSION 3.3.9)`。

## 触发条件
- 构建系统: cmake（configure_file 生成 fftw3.pc）
- 阶段: 安装后元数据校验（pkg-config / CMake config 版本核对）
- 上游 FFTW 3.3.10 tarball 的 CMakeLists.txt 第 282 行写死 `FFTW_VERSION 3.3.9`（Autotools 的 configure.ac 则用 `FFTW_MAJOR_VERSION.FFTW_MINOR_VERSION` 正确推导 3.3.10）

## 根因分析
上游 3.3.10 发布时仅更新了 Autotools 版本号，遗漏了 CMakeLists.txt 中的
`FFTW_VERSION` 变量，导致同一 tarball 两套构建系统产生不一致的版本元数据。
CMake 通过 `configure_file(fftw.pc.in fftw3.pc @ONLY)` 将 `@VERSION@` 替换为
`${FFTW_VERSION}`，于是 `.pc` 文件携带错误版本号；CMake 的
`FFTW3ConfigVersion.cmake` 同样基于该变量。

## 解决方案

### 推荐方案
新增配方补丁 `patches/0002-fftw-version.patch`，将
`set (FFTW_VERSION 3.3.9)` 改为 `set (FFTW_VERSION 3.3.10)`，并在
conandata.yml 的 patches 列表注册（patch_type: upstream-bugfix），保证
conan create 从干净 tarball 可复现。验证：
```bash
pkg-config --modversion fftw3   # 期望 3.3.10
```

### 禁止做法
- ❌ 直接修改 conan cache 内已解压源码或绕过 conandata.yml 手工 sed 源码（破坏配方可复现性，W3/CI 复现失败）。
- ❌ 把版本不一致只写进 notes/PR 正文而不打补丁（若允许打补丁时，会导致 pkg-config 消费者版本判断错误长期存在）。

## 验证
```bash
patch -p1 < patches/0002-fftw-version.patch
pkg-config --modversion fftw3 | grep -q '^3.3.10'
```

## 关联条目
- 相关: E207（OHOS CMake SONAME/相对路径链接，同为 CMake 元数据/链接元数据问题）
- 同类: 任何 CMake 写死版本号而 Autotools 推导真实版本的库（pkg-config Version 字段不一致）
