# abiword-plugin-openwriter 3.0.8 可行性报告（OHOS PC 适配）

## 上游基本信息

| 项目 | 值 |
|------|-----|
| 上游仓库 | https://gitlab.gnome.org/World/AbiWord |
| 镜像 | https://github.com/AbiWord/abiword |
| 插件路径 | plugins/openwriter/ |
| 上游版本 | 3.0.8 |
| 发布日期 | 2026-02-18 |
| 协议 | GPL-2.0-or-later |
| 源码包 | AbiWord-release-3.0.8.tar.bz2 |
| 包大小 | ~7.5 MB(完整 AbiWord 源码) |
| Alpine 打包 | abiword-plugin-openwriter-3.0.8-r0 |

## 适配路径

### 路径 A：基础适配（必须）

- [ ] 下载并校验 AbiWord 3.0.8 tarball
- [ ] 提取 `plugins/openwriter/` 到独立工作区
- [ ] 分析 openwriter 的运行时依赖
- [ ] 写 conanfile.py（autotools 配方）
- [ ] conandata.yml 中标注 subpath（从 AbiWord 主源码提取）
- [ ] 交叉编译 .so → OHOS HNP worker（aarch64-linux-gnu）
- [ ] test_package：CMake 消费者测试，调用 openwriter 关键 API

### 路径 B：贡献创新

- [ ] 真机 ODT 文件导入/导出测试
- [ ] 性能对比 vs 上游 AbiWord
- [ ] OHOS 沙箱兼容性分析

## 依赖分析（待确认）

```
abiword-plugin-openwriter
├── abiword 主库 (libAbiWord)
│   ├── glib (>= 2.40)
│   ├── libxml2 (>= 2.6)
│   ├── pango
│   ├── fribidi
│   ├── cairo
│   └── ...
├── libgsf (gnome structured file)
│   └── glib
└── 其他（待 openwriter configure.ac 分析）
```

## 风险与挑战

| 风险 | 缓解 |
|------|------|
| abiword 主库未适配 | 必须先完成 archives/a/abiword/3.0.8/ 移植 |
| libgsf 未在 OHOS 归档 | 检查 archives/g/gsf 是否存在，不存在则先适配 |
| ODT 复杂格式（CSS/嵌入对象） | 测试用例要覆盖真实 .odt 文件 |
| 字符串本地化 | abiword 用 gettext，OHOS 移植需关闭 NLS 或自实现 |

## 已知依赖归档状态

| 依赖 | 归档状态 | 备注 |
|------|---------|------|
| glib | 已归档 (archives/g/glib/) | - |
| libxml2 | 已归档 (archives/l/libxml2/) | - |
| pango | 需查 | - |
| fribidi | 需查 | - |
| cairo | 需查 | - |
| libgsf | 需查 | - |
| abiword 主库 | **未归档** | 必须先移植 |

## 时间估算

- 阶段 0：abiword 主库适配(预计 2-3 周)
- 阶段 1：openwriter 单独归档 + conan 配方 (1 周)
- 阶段 2：交叉编译 + 烟雾测试 (3 天)
- 阶段 3：真机回归 (3-5 天)
- 阶段 4：PR review & merge (1 周)
