# jpi-analyzer 0.2.0-git20260502.823a948 编译笔记

## 基本信息

- **软件名称**: jpi-analyzer
- **版本**: 0.2.0-git20260502.823a948
- **上游仓库**: https://github.com/unicornlines/JPI-Parser
- **许可证**: MIT
- **语言**: Python >= 3.10（纯 Python，无 C 扩展）

## 版本锚定

- 上游 tag `v0.2.0` 指向 commit `e1a34c3`（多一个仅改 pyproject author 的提交），
  与产品版本 0.2.0 的实际发布内容不一致。
- 本配方按版本锚定要求固定在 commit `823a948bf005941275b9c6d93bfc8037be63239d`
  （2026-05-02），源码归档 URL 直接使用 commit 归档，SHA256 固定于 conandata.yml。

## 构建信息

### 构建系统

- **类型**: 纯 Python 包（PEP 517, setuptools.build_meta）
- **构建方式**: `pip install --no-deps --target`
- 构建隔离（build isolation）从网络拉取 setuptools/wheel，与 click/8.4.2 同路径，
  已在 ohos-aarch64 设备验证可行。

### 依赖项

#### 核心依赖

- click >= 8.1 → 使用仓内已发布的 `click/8.4.2`（Conan 依赖，经 runenv PYTHONPATH
  传播给消费者，不进 pip 依赖树）

#### 可选依赖

- 无

## 适配说明

### OHOS 平台适配

jpi-analyzer 是纯 Python 包，无平台相关编译。适配点集中在目标环境运行面：

1. 包本体与依赖 click 均通过 Conan 注入的 `PYTHONPATH` 在 ohos-aarch64 目标
   环境解析导入；
2. pip 安装的 console scripts（`jpi-analyzer`、`jpia`）落在 `<pkg>/bin`，shebang
   指向设备解释器，可直接执行。

### 已知限制

1. 需要 Python >= 3.10（设备 python 3.12.9 满足）
2. 设备系统 site-packages 无 setuptools，构建依赖由 pip build isolation 联网获取

## 验证方法

### test_package

上游（commit 823a948 与 e1a34c3 两棵树）无 tests/ 目录、pyproject 无 pytest/test
extra、无 CI workflow，README 仅为手动 CLI 示例 → 按 NO_UPSTREAM_TESTS 记录。

替代验证为本移植新增的鸿蒙特有端到端测试（test_package/test_ohos_jpi_analyzer.py）：

1. 目标环境经 Conan 注入的 PYTHONPATH 正确解析导入 jpi_analyzer 与 click；
2. 在 aarch64 目标解释器下运行（HarmonyOS PC 设备）；
3. 合成一个最小合法 .JPI 样本文件，真实执行打包出的 console scripts：
   `jpi-analyzer info` 解析出航班元数据，`csv` 解码数据记录并写出
   flight_1.csv（含真实量测值），`jpia` 别名同样可执行。

## 交付物

- Python 包文件（jpi_analyzer 包，5 个模块）
- console scripts: `<pkg>/bin/jpi-analyzer`、`<pkg>/bin/jpia`

## 参考资料

- 上游仓库: https://github.com/unicornlines/JPI-Parser
- 文件格式说明: 上游 filespec.md（JPI EDM 二进制格式）
