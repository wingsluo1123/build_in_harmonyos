# 适配笔记 — ki18n 6.19.0

## 2026-07-21 正式适配

### 上游信息
- homepage: https://invent.kde.org/frameworks/ki18n
- 源码: https://download.kde.org/stable/frameworks/6.19/ki18n-6.19.0.tar.xz
- SHA256: 608ff2634cd19736a8091c750c71b23db0b33fd81e82fb9fc4bcce76712284a6（占位填入，CI 首次构建实测校验）
- 构建系统: CMake（find_package(ECM 6.19 REQUIRED) + Qt6 + gettext）

### 拓扑序（R36）
```
extra-cmake-modules 6.19.0 ✅ 就位（MR !2983，R-CI8 三修复已推）
qtbase 6.11.1          ✅ 就位（MR !2999，6.12 切版 + OHOS 真变量名）
ki18n 6.19.0          ← 本配方（依赖 ECM + Qt6 qtbase + gettext）
karchive 6.19.0       → 下游（依赖 ki18n + ECM）
kdoctools 6.19.0-r0   → 最终目标（依赖 karchive + ECM）
```

### 配方策略
- 源码编译范式（R39 合规 KDE 官方源 download.kde.org）
- generators = "CMakeToolchain", "CMakeDeps"（与 ECM R-CI2/R-CI4 同范式）
- requirements 显式声明 ECM 6.19.0 + qtbase >=6.5 <7（Qt6 待赛事发布）
- package() 精确复制 KF6I18n*.so + *.h + KF6I18nConfig*.cmake（避 R19 包污染）
- test_package test() 用 self.run(self.build_folder/test_ki18n, env="conanrun")（与 ECM R-CI7 同范式）

### R34 实质调用 API
test_ki18n.cpp 调用 `kxi18n("Hello")` → KLocalizedString 验证链通（非空链接测试）。

### 已知限制
- 本地开发机缺 Qt6 预构建 + gettext，conan create configure 阶段可能撞 Qt6/find_package 边界
- CI worker 需预置 Qt6 qtbase + gettext（鸿蒙赛事基础设施层）
- 本配方假设 ECM + qtbase 两依赖都正确（用户决断），等 CI 验证反馈真可行性
