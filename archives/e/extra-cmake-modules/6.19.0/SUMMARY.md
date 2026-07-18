# extra-cmake-modules 6.19.0 — 适配摘要

## 软件信息
- **名称**：extra-cmake-modules (ECM)
- **版本**：6.19.0
- **类型**：cmake-only 模块包（无 C/C++ 编译产物）
- **上游**：https://download.kde.org/stable/frameworks/6.19/extra-cmake-modules-6.19.0.tar.xz
- **SHA256**：a4f0c1d8181f43e9af4b9b44696c77760b5bc9dae5bdb921f090bce664e9ca84
- **依赖**：零运行时依赖

## 构建信息
- **构建系统**：CMake
- **平台**：OHOS / Linux / macOS / Windows
- **状态**：built（cmake configure → make → make install DESTDIR → ctest 全部 EXIT=0）

## 适配产物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（cmake-only，无 cpp_info.libs） |
| conandata.yml | 源码 URL + SHA256 声明 |
| test_package/ | L1 官方测试（find_package(ECM) + ECMQmLoader 宏） |
| test_package/MANIFEST.yml | 上游测试声明 |
| notes.md | 适配笔记（含 DESTDIR 双重路径发现） |
| manifest.yaml | 元数据 |

## 知识图谱新增
- 无新增 E 条目（本次适配无错误模式需沉淀）
- 平台陷阱：cmake 报 "System is unknown to cmake" 非阻塞，自动 fallback Linux

## 下游链位置
kdoctools 6.19.0 链第一环（最底层依赖）：
```
ECM 6.19.0 (本次) → ki18n 6.19.0 → karchive 6.19.0 → kdoctools 6.19.0
                  ↑               ↑
                  Qt6 (待适配) ───┘
```

## PR 原子性 (W2)
本 PR 仅包含 ECM 6.19.0 配方及知识产物，未触碰 SKILL 框架文件。
