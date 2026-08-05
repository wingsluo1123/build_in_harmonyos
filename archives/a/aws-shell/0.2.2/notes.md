# aws-shell 0.2.2 适配笔记

## 编译环境
- 构建系统: python (pip/setup.py)
- 编译日期: 2026-08-05
- 状态: built

## 编译步骤
- `pip install --no-deps --target=staging .` → 安装成功
- 构建为 Conan 配方，使用 pip 驱动构建

## 遇到的问题与解决方案
- aws-shell 0.2.2 依赖 prompt-toolkit >=1.0.0,<1.1.0
- prompt-toolkit 1.x 使用 `from collections import Mapping`，Python 3.12 已移除
- prompt-toolkit 1.x 和 3.x API 完全不兼容，aws-shell 无法正常使用交互功能
- 依赖版本兼容性问题，非 OpenHarmony 平台限制
- 2 个补丁为 Python egg-info 元数据修补 (PKG-INFO, entry_points.txt)
- test_package 使用 importlib 直接加载 awsshell.fuzzy/substring 模块测试 API，
  绕过 __init__.py 对 botocore/prompt-toolkit 的依赖

## 验证结果
- Conan Verify: PASS (G1/G2/G3/G4/L2/L4/L5)
- W3 Local CI Simulation: PASS
- test_package: PASS (API calls to fuzzy_search and substring_search)

---

**编译结束**: 2026-08-06 00:13
**最终状态**: built
