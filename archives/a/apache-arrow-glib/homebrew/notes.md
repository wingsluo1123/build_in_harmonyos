# apache-arrow-glib homebrew 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-18
- 编译器: clang/clang++
- 状态: failed（G2 conan create 待 CI 执行，Windows 本地无 OHOS 工具链）

## 编译步骤

```bash
# 源码下载后进入 c_glib/ 子目录
cd c_glib
meson setup build --prefix=$DEFAULT_PREFIX -Ddoc=false -Dgtk_doc=false -Dvapi=false
meson compile -C build
meson install -C build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 在 Windows 上失败 | 本地无 OHOS 交叉编译工具链（clang/meson/ninja/pkg-config） | 待 CI 流水线执行编译验证 |

## 源码修改

无须修改上游源码。构建入口为 Apache Arrow 24.0.0 完整源码中的 `c_glib/` 子目录。

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| apache-arrow | 24.0.0 | 已编译（archives/a/apache-arrow/24.0.0/） |
| glib | 2.84.0 | 已编译（archives/g/glib/2.84.0/） |
| meson | >= 0.61.2 | 框架内置 |

## 验证结果

- G0 预构建风险评估：通过（E007 提示为 autotools 误判，本库使用 Meson）
- G1 配方完整性：通过
- G2 conan create：待 CI 验证

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 构建食谱 |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | Conan L1 消费者测试（CMake + C） |

## 注意事项

- 源码与 apache-arrow 24.0.0 共用同一 tarball，构建入口在 `c_glib/` 子目录
- 上游测试为 Ruby 脚本（180+ 文件），鸿蒙 PC 无 Ruby 运行时，无法在 CI 中运行
- 构建时需关闭文档（-Ddoc=false）和 Vala 绑定（-Dvapi=false）以降低依赖要求
- Apache Arrow 已编译为共享库 + 静态库，arrow-glib 需要 ARROW_COMPUTE/ARROW_CSV/ARROW_FILESYSTEM/ARROW_JSON 模块开启

---

**编译结束**: 2026-07-18 17:10
**最终状态**: failed（待 CI 编译验证）
