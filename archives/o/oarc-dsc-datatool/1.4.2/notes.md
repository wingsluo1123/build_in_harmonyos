# oarc-dsc-datatool 1.4.2 — 编译笔记

## 软件简介

**oarc-dsc-datatool** (DSC DataTool) 是 DNS-OARC 开发的纯 Python 包，提供
处理 DNS Statistics Collector (DSC) 数据的工具。它是命令行工具
`dsc-datatool` 的主 Python 模块。

- 上游仓库: https://github.com/DNS-OARC/dsc-datatool (GitHub 已 ARCHIVED)
- 版本: 1.4.2 (上游 tag v1.4.2)
- 许可证: BSD-3-Clause (Copyright (c) 2016-2024 OARC, Inc.)
- 构建系统: setuptools (pip install .)
- 包类型: 纯 Python 包，无 C 扩展

## 依赖

### setup.py install_requires (运行时)
- maxminddb >= 1.2.0 (GeoIP 数据库读取)
- PyYAML >= 3.11 (YAML 配置文件解析)

### 上游测试依赖
- pytest >= 4 (测试框架)
- coverage (覆盖率)
- watchdog (文件监视)

### 构建依赖 (Conan recipe)
- 无 C/C++ 依赖
- 使用 Conan 的 sys.executable (Python 3.12.9)

## 适配说明

### 1. 纯 Python 包适配
- 使用 `pip install . --prefix=... --no-deps` 安装到 staging prefix
- `--no-deps`: 不从 PyPI 拉取运行时依赖（maxminddb, PyYAML），这些由
  下游消费者自行管理或通过 conan recipe 的 requirements() 声明
- `package_info()` 通过 `runenv_info.append_path("PYTHONPATH", ...)` 导出
  site-packages 路径，供下游消费者使用

### 2. 平台兼容 (R32)
- `settings = "os", "arch"` — 纯 Python 包只需 os/arch 标识平台
- `validate()` 中 `settings.os not in ("Linux", "OHOS")` 检查 — R32 规范

### 3. 测试策略
- 上游测试 (tests/): test.sh (shell 集成测试) + test_main.py / test_objects.py (pytest)
- 上游 test.sh 依赖 `dsc-datatool` CLI 二进制在 PATH 中 + InfluxDB output 插件
- 上游 test_main.py / test_objects.py 依赖 pytest + maxminddb 运行时
- 在 OHOS R32 平台上 maxminddb / influxdb-client 可能受限
- 故 `upstream_test_in_build=false`，由 test_package 做 7 个消费者 smoke test

### 4. 源码获取
- GitHub 仓库已 ARCHIVED，但 tag v1.4.2 存在
- 源码 tarball 从 GitHub archive 下载:
  https://github.com/DNS-OARC/dsc-datatool/archive/refs/tags/v1.4.2.tar.gz
- SHA256: e2f4e5e5072f2c6f44505b4fcd342dd23d4036972de802e1c1ee46595e44210f

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 配方完整性 | ✅ | conanfile.py + conandata.yml + test_package/ 完整 |
| G2 conan create | ✅ | 本地源码构建成功，pip install . 产出 dsc_datatool 模块 |
| L2 smoke test | ✅ | 7 个 smoke test 全部通过 (模块导入/版本/类/功能) |
| R32 OHOS 兼容 | ✅ | validate() 中 in ("Linux", "OHOS") 检查 |
| R34 实质依赖 | ✅ | test.sh 实质性调用被测包 API (import, class, repr) |
| R39 官方源 | ✅ | URL 指向 GitHub 官方 archive |

## 包结构

```
dsc_datatool/
  __init__.py          # 主模块: Dataset, Dimension, Input, Output, Generator, Transformer
  input/
    dat.py             # DAT 输入插件
    xml.py             # XML 输入插件
  output/
    influxdb.py        # InfluxDB 输出插件
    prometheus.py      # Prometheus 输出插件
  generator/
    client_subnet_authority.py   # 客户端子网权限生成器
    client_subnet_country.py     # 客户端子网国家生成器
  transformer/
    labler.py          # 标签转换器
    net_remap.py       # 网络重映射转换器
    re_ranger.py       # 范围重组转换器
```
