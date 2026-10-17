# sidplay-libs 2.1.1 适配笔记

## 编译环境
- 构建系统: autotools（顶层 configure 自定义递归脚本，in-source only）
- 编译日期: 2026-10-17
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# in-source 构建（Conan 配方 folders.build="." 强制）
CXXFLAGS="-fPIC -O2 -Wno-c++11-narrowing -Wno-narrowing" \
  ./configure --prefix=$PREFIX --enable-static --disable-shared
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2004 年版脚本无 OHOS 分支（E007） | 打补丁输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 拒绝 linux-ohos 三元组 | 老脚本 OS 列表无 ohos（E007） | 添加 -linux-ohos* 识别 |
| 3 | config.status mktemp Permission denied | umask 077 在 HMDFS setgid 目录不可写（E112） | 全部 configure/config.status umask 077→022 |
| 4 | xsid.cpp int8_t 数组窄化错误 | C++11 窄化：'\x80' 等溢出 int8_t | sampleConvertTable int8_t→int + -Wno-c++11-narrowing |
| 5 | SmartPtr.h 未声明成员 | 模板两阶段查找，派生类需 this-> | setBuffer 内成员加 this-> |
| 6 | SidUsage.h extra qualification | 老代码 operator= 带类名限定 | 去掉 "sid2_usage_t::" 限定 |
| 7 | conan create out-of-source 失败 | 顶层 configure 递归 cd 硬编码相对路径 | basic_layout + folders.build="."（in-source） |

## 源码修改

22 个补丁（patches/0001-0022）：config.guess/config.sub（6 组 × OHOS 识别）、configure/config.status umask、SmartPtr.h、SidUsage.h、xsid.cpp/h。

## 依赖版本

无外部依赖（纯 C++ 老代码，libtool 2.x 内嵌）。

## 验证结果

- `make check`：无注册测试（2004-era autotools），exit 0
- `conan create`：成功（G1/G2/G3/G4 门禁通过）
- test_package：构造 sidplay2 引擎 + SidDatabase，输出 `OK: sidplay2 engine info version=2.1.1 channels=1`

## 注意事项

- 此包是 sidplay 2.0.9 的**依赖**（R36 拓扑序：先发布本包，再构建 sidplay）
- 官方 SourceForge 源仍可用；GitHub 镜像 sf-is-evil/sidplay2 只含 sidplay/ CLI 子目录，不含三个库
- 构建器静态库位于 `lib/sidplay/builders/`，sidplay 通过 pkg-config 的 `builders` 变量定位
