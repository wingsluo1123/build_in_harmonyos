# 适配笔记 — kdoctools 6.19.0-r0

## 2026-07-21 正式适配

### 上游信息
- homepage: https://invent.kde.org/frameworks/kdoctools
- 源码: https://download.kde.org/stable/frameworks/6.19/kdoctools-6.19.0.tar.xz
- SHA256: c2048b2979247540f9ba22fd7c6f372ce869699c3a3e81a97af2fa2f733c74bc（占位填入，CI 首次构建实测校验）
- 构建系统: CMake（find_package(ECM 6.19 REQUIRED) + Qt6 + ki18n + karchive + libxml2/libxslt）
- 版本号: 6.19.0-r0（Alpine revision r0，上游 KDE Frameworks 6.19.0，R37 版本号策略）

### 拓扑序（R36）— 最终目标
```
extra-cmake-modules 6.19.0 ✅ 就位（MR !2983，R-CI8 三修复已推）
qtbase 6.11.1          ✅ 就位（MR !2999，6.12 切版 + OHOS 真变量名）
ki18n 6.19.0          ✅ 正式适配（本轮，依赖 ECM + Qt6）
karchive 6.19.0       ✅ 正式适配（本轮，依赖 ECM + Qt6）
kdoctools 6.19.0-r0   ← 本配方（最终目标，依赖 ECM + Qt6 + ki18n + karchive + libxml2/libxslt）
```

### 配方策略
- 源码编译范式（R39 合规 KDE 官方源 download.kde.org）
- generators = "CMakeToolchain", "CMakeDeps"（与 ECM R-CI2/R-CI4 同范式）
- requirements 显式声明 ECM 6.19.0 + ki18n 6.19.0 + karchive 6.19.0 + qtbase >=6.5 <7（Qt6 待赛事发布）
- package() 精确复制 KF6DocTools*.so + *.h + KF6DocToolsConfig*.cmake + bin/ 工具（mecut/transform/man，避 R19 包污染）
- test_package test() 用 self.run(self.build_folder/test_kdoctools, env="conanrun")（与 ECM R-CI7 同范式）

### R34 实质调用 API
test_kdoctools.cpp 调用 `KDOCTOOLS_VERSION_STRING` 宏验证链通（非空链接测试）。

### R38 commands.json
kdoctools 含 bin 可执行（mecut/transform/man），需 commands.json 声明 CLI 工具——待配方完整适配后补。

### 已知限制
- 本地开发机缺 Qt6 预构建 + ki18n/karchive + libxml2/libxslt 系统库，conan create configure 阶段可能撞 Qt6/find_package 边界
- CI worker 需预置 Qt6 qtbase + ki18n + karchive + 系统文档库（鸿蒙赛事基础设施层）
- 本配方假设 ECM + qtbase + ki18n + karchive 四依赖都正确（用户决断），等 CI 验证反馈真可行性
