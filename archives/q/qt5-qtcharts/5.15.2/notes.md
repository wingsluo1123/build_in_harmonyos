# qt5-qtcharts 5.15.2 编译笔记

## 编译环境
- 平台: aarch64-linux-ohos (鸿蒙)
- 编译器: clang++ (OHOS SDK, clang 15.0.4)
- Qt5版本: 5.15.2
- 构建系统: qmake (Qt5 addon module)

## 依赖
- qt5-qtbase 5.15.2 (Qt Core, Gui, Widgets, Network)
  - 远程制品仓中 qt5-qtbase/5.15.2 使用 `-no-widgets` 构建，缺少 Qt5Widgets 模块
  - 本地归档 qt5-qtbase/5.15.2.1 包含完整 Widgets 支持但未发布到制品仓
- qt5-qtdeclarative 5.15.2 (Qml, Quick, QmlModels)
  - 制品仓中不存在 qt5-qtdeclarative/5.15.2
  - 本地归档中也不存在 qt5-qtdeclarative 的任何版本

## 源码结构
```
qtcharts-everywhere-src-5.15.2/
├── qtcharts.pro          # 主项目文件
├── .qmake.conf           # 模块版本配置 (MODULE_VERSION = 5.15.2)
├── src/
│   ├── src.pro           # 子目录: charts + chartsqml2
│   ├── charts/           # C++ 图表库 (libQt5Charts.so)
│   └── chartsqml2/       # QML 插件 (libqtchartsqml2.so, 需要 Qt5Quick)
├── include/              # 头文件
├── tests/                # 自动测试
├── examples/             # 示例
└── plugins/              # 插件
```

### qtcharts.pro 依赖检查
```qmake
requires(qtHaveModule(widgets))     # 必须有 Qt5Widgets
qtHaveModule(quick) {              # 可选: 如果有 Qt5Quick 才构建 QML 插件
    SUBDIRS += chartsqml2
}
```

## 编译步骤

### 1. 设置环境（使用 Conan 提供的 qt5-qtbase）
```bash
QT5_BASE=<conan_package_folder>/p
export PATH="$QT5_BASE/bin:$PATH"
export QTDIR="$QT5_BASE"
export LD_LIBRARY_PATH="$QT5_BASE/lib:$LD_LIBRARY_PATH"
```

### 2. qmake 配置
```bash
$QT5_BASE/bin/qmake qtcharts.pro
```
- 需要修复 qt5-qtbase 包的 .pri 文件中的硬编码路径（指向已删除的 build 目录）
- 创建符号链接: build_path → package_folder

### 3. 编译
```bash
make -j2
```
- 当 qt5-qtbase/5.15.2 缺少 Widgets 时，qmake 输出 "Some of the required modules (qtHaveModule(widgets)) are not available." 并跳过构建

## 阻塞原因

### 依赖缺失
1. **qt5-qtdeclarative/5.15.2**: 制品仓中完全不存在
2. **Qt5Widgets 模块**: qt5-qtbase/5.15.2 制品使用 `-no-widgets` 构建

### Conan 配方验证 (conan-verify G2)
```
ERROR: Package 'qt5-qtdeclarative/5.15.2' not resolved:
  Unable to find 'qt5-qtdeclarative/5.15.2' in remotes.
  Required by 'qt5-qtcharts/5.15.2@ohpcd/stable'
```

### 本地 CI 模拟 (W3)
```
[fail] qt5-qtcharts/5.15.2 — conan create failed
[hint] 依赖包未构建, 请先提交依赖包的 PR 并等待 CI 通过
```

## 解决方案
1. 先适配并发布 qt5-qtdeclarative/5.15.2 到制品仓
2. 发布 qt5-qtbase/5.15.2.1 (包含 Widgets 模块) 到制品仓
3. 依赖发布后，重新运行 conan-verify 验证 qt5-qtcharts 配方

## Conan 配方
- conanfile.py: 已创建，正确声明 qt5-qtbase/5.15.2 和 qt5-qtdeclarative/5.15.2 依赖
- conandata.yml: 已配置官方源码 URL 和 sha256
- test_package/: 已创建 CMake-based 测试，验证 Qt5Charts 库链接

## 编译结束
**最终状态**: failed (dependency_missing)
**缺失依赖**: qt5-qtdeclarative/5.15.2, qt5-qtbase (with Widgets)

---

**编译结束**: 2026-08-08
**最终状态**: failed (dependency_missing)
